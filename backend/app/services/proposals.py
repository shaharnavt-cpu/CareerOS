"""Deterministic validation, deduplication, and proposal formatting."""

from __future__ import annotations

import hashlib
import json
import re
from difflib import SequenceMatcher

from app.schemas.knowledge import (
    Clarification,
    ClarificationReason,
    EntityType,
    EvidenceReference,
    ExistingMemoryItem,
    ExtractedCandidate,
    KnowledgeProposal,
    NormalizedSource,
    ProposalOperation,
    ProposalRelationship,
    SemanticAssessment,
)
from app.services.confidence import ConfidenceAggregator


class ReasoningValidationError(ValueError):
    """Raised when provider output violates deterministic pipeline rules."""


class DuplicateDetector:
    """Find likely canonical duplicates without asking the provider to decide."""

    threshold = 0.9

    def find(
        self,
        entity_type: EntityType,
        value: dict[str, object],
        existing_memory: list[ExistingMemoryItem],
    ) -> ExistingMemoryItem | None:
        candidate_label = self._label(value)
        if not candidate_label:
            return None

        for item in existing_memory:
            if item.entity_type is not entity_type:
                continue
            existing_label = self._label(item.value)
            if (
                existing_label
                and SequenceMatcher(None, candidate_label, existing_label).ratio()
                >= self.threshold
            ):
                return item
        return None

    @staticmethod
    def _label(value: dict[str, object]) -> str:
        for key in ("normalized_name", "name", "title", "institution_name"):
            label = value.get(key)
            if isinstance(label, str):
                return re.sub(r"\W+", " ", label.casefold()).strip()
        return ""


class ProposalBuilder:
    """Convert untrusted semantic assessments into safe proposals."""

    _required_fields = {
        EntityType.EDUCATION: ("institution_name",),
        EntityType.PROGRAM: ("name",),
        EntityType.EXPERIENCE: ("title", "organization_name", "experience_type"),
        EntityType.PROJECT: ("title",),
        EntityType.ACHIEVEMENT: ("title",),
        EntityType.SKILL: ("name", "normalized_name"),
    }
    _relationship_targets = {
        EntityType.PROGRAM: {
            EntityType.EDUCATION,
            EntityType.EXPERIENCE,
            EntityType.PROJECT,
            EntityType.ACHIEVEMENT,
        },
        EntityType.SKILL: {
            EntityType.EDUCATION,
            EntityType.EXPERIENCE,
            EntityType.PROJECT,
            EntityType.ACHIEVEMENT,
            EntityType.PROGRAM,
        },
    }

    def __init__(
        self,
        confidence: ConfidenceAggregator | None = None,
        duplicates: DuplicateDetector | None = None,
    ) -> None:
        self._confidence = confidence or ConfidenceAggregator()
        self._duplicates = duplicates or DuplicateDetector()

    def build(
        self,
        source: NormalizedSource,
        candidates: list[ExtractedCandidate],
        assessments: list[SemanticAssessment],
        existing_memory: list[ExistingMemoryItem],
    ) -> list[KnowledgeProposal]:
        candidate_by_id = {candidate.id: candidate for candidate in candidates}
        assessment_by_id = {
            assessment.candidate_id: assessment for assessment in assessments
        }
        if set(candidate_by_id) != set(assessment_by_id):
            raise ReasoningValidationError(
                "semantic output must contain exactly one assessment per candidate"
            )

        proposal_ids = {
            candidate_id: self._proposal_id(source.id, assessment)
            for candidate_id, assessment in assessment_by_id.items()
        }
        proposals: list[KnowledgeProposal] = []

        for candidate in candidates:
            assessment = assessment_by_id[candidate.id]
            self._validate_required_fields(assessment)
            evidence = EvidenceReference(
                source_id=source.id,
                source_type=source.source_type,
                title=source.name,
                excerpt=candidate.evidence_excerpt,
                location=candidate.location,
            )
            score = self._confidence.aggregate(candidate, assessment, has_evidence=True)
            reason = self._confidence.clarification_reason(
                score, assessment, has_evidence=True
            )
            duplicate = self._duplicates.find(
                assessment.entity_type, assessment.proposed_value, existing_memory
            )
            relationships = self._valid_relationships(
                assessment,
                assessment_by_id,
                proposal_ids,
            )

            proposals.append(
                KnowledgeProposal(
                    id=proposal_ids[candidate.id],
                    entity_type=assessment.entity_type,
                    proposed_value=assessment.proposed_value,
                    operation=(
                        ProposalOperation.UPDATE
                        if duplicate
                        else ProposalOperation.CREATE
                    ),
                    confidence=score,
                    evidence=[evidence],
                    reasoning_summary=assessment.reasoning_summary,
                    clarification=self._clarification(
                        reason, assessment, candidate.raw_value
                    ),
                    duplicate_of=duplicate.id if duplicate else None,
                    relationships=relationships,
                )
            )

        return self._merge_exact_duplicates(proposals)

    def _validate_required_fields(self, assessment: SemanticAssessment) -> None:
        missing = [
            field
            for field in self._required_fields[assessment.entity_type]
            if not assessment.proposed_value.get(field)
        ]
        if missing:
            raise ReasoningValidationError(
                f"{assessment.entity_type.value} output missing required fields: "
                + ", ".join(missing)
            )

    def _valid_relationships(
        self,
        assessment: SemanticAssessment,
        assessment_by_id: dict[str, SemanticAssessment],
        proposal_ids: dict[str, str],
    ) -> list[ProposalRelationship]:
        valid: list[ProposalRelationship] = []
        allowed_targets = self._relationship_targets.get(assessment.entity_type, set())
        for relationship in assessment.relationships:
            target_id = relationship.target_proposal_id
            target = assessment_by_id.get(target_id)
            if not target or target_id == assessment.candidate_id:
                continue
            if target.entity_type not in allowed_targets:
                continue
            valid.append(
                ProposalRelationship(
                    target_proposal_id=proposal_ids[target_id],
                    relationship_type=relationship.relationship_type.upper(),
                )
            )
        return valid

    def _clarification(
        self,
        reason: ClarificationReason | None,
        assessment: SemanticAssessment,
        raw_value: str,
    ) -> Clarification | None:
        if reason is None:
            return None

        subject = self._display_label(assessment.proposed_value) or raw_value
        question = assessment.clarification_question or ""
        if self._is_generic_question(question, subject):
            question = self._specific_question(reason, subject, assessment)

        if reason is ClarificationReason.MISSING_EVIDENCE:
            detail = f'No source evidence supports "{subject}".'
        elif reason is ClarificationReason.CONFLICTING_EVIDENCE:
            detail = (
                f'Conflicting source values were found for "{subject}": '
                + "; ".join(assessment.conflicting_evidence)
            )
        else:
            detail = (
                f'The classification or details for "{subject}" are below the '
                "confidence threshold."
            )
        return Clarification(question=question, reason=reason, detail=detail)

    @staticmethod
    def _is_generic_question(question: str, subject: str) -> bool:
        folded = question.casefold().strip()
        subject_tokens = [
            token for token in re.findall(r"\w+", subject.casefold()) if len(token) > 2
        ]
        generic_prefixes = (
            "tell me more",
            "can you clarify",
            "what else",
            "please clarify",
        )
        return (
            len(folded) < 10
            or folded.startswith(generic_prefixes)
            or not any(token in folded for token in subject_tokens)
        )

    @staticmethod
    def _specific_question(
        reason: ClarificationReason,
        subject: str,
        assessment: SemanticAssessment,
    ) -> str:
        if reason is ClarificationReason.MISSING_EVIDENCE:
            entity_label = assessment.entity_type.value.lower()
            return f'What source can support the proposed {entity_label} "{subject}"?'
        if reason is ClarificationReason.CONFLICTING_EVIDENCE:
            return f'Which source value should CareerOS use for "{subject}"?'
        missing = (
            ", ".join(assessment.missing_fields) or "its classification and details"
        )
        return (
            f'I found "{subject}" but could not confidently determine {missing}. '
            "What should CareerOS record?"
        )

    @staticmethod
    def _display_label(value: dict[str, object]) -> str:
        for key in ("name", "title", "institution_name", "organization_name"):
            label = value.get(key)
            if isinstance(label, str):
                return label.strip()
        return ""

    @staticmethod
    def _proposal_id(source_id: str, assessment: SemanticAssessment) -> str:
        serialized = json.dumps(
            assessment.proposed_value, sort_keys=True, separators=(",", ":")
        )
        digest = hashlib.sha256(
            f"{source_id}:{assessment.candidate_id}:{serialized}".encode()
        ).hexdigest()[:24]
        return f"proposal-{digest}"

    @staticmethod
    def _merge_exact_duplicates(
        proposals: list[KnowledgeProposal],
    ) -> list[KnowledgeProposal]:
        unique: dict[tuple[EntityType, str], KnowledgeProposal] = {}
        for proposal in proposals:
            label = DuplicateDetector._label(proposal.proposed_value)
            key = (proposal.entity_type, label)
            if not label or key not in unique:
                unique[key] = proposal
                continue
            existing = unique[key]
            seen = {
                (item.source_id, item.location, item.excerpt)
                for item in existing.evidence
            }
            existing.evidence.extend(
                item
                for item in proposal.evidence
                if (item.source_id, item.location, item.excerpt) not in seen
            )
            existing.confidence = max(existing.confidence, proposal.confidence)
        return list(unique.values())
