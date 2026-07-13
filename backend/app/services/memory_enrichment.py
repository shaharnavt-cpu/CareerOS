"""Create, review, and project approved evidence enrichment onto Career Memory."""

from __future__ import annotations

import json
import re
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    CanonicalMemoryRecord,
    CareerMemoryEnrichment,
    ListeningEvidence,
    ListeningSource,
    ReviewProposal,
)
from app.schemas.enrichments import (
    CareerMemoryTarget,
    EnrichmentCreateRequest,
    EnrichmentStatus,
    EnrichmentType,
    EnrichmentUpdateRequest,
    EnrichmentView,
    MemoryIdentityResolution,
    MemoryResolutionKind,
    RecommendedReviewAction,
)
from app.schemas.knowledge import (
    DEMO_USER_ID,
    ApprovalState,
    DurableReviewStatus,
    KnowledgeProposal,
)

PARSE_QUALITY_WARNING = (
    "CareerOS found limited project-specific text in this source. Paste the "
    "abstract, methods, or results section to enrich this memory."
)


class EnrichmentNotFoundError(LookupError):
    """Raised for unavailable user-scoped enrichment resources."""


class EnrichmentStateError(ValueError):
    """Raised when enrichment would cross the approved-memory boundary."""


class ProjectEnrichmentExtractor:
    """Extract only text-supported project fields using deterministic rules."""

    _labels = {
        "project title": "project_title",
        "title": "project_title",
        "project goal": "project_goal",
        "goal": "project_goal",
        "objective": "project_goal",
        "research question": "research_question",
        "question": "research_question",
        "data": "data_or_inputs",
        "input": "data_or_inputs",
        "inputs": "data_or_inputs",
        "data/input": "data_or_inputs",
        "data or inputs": "data_or_inputs",
        "method": "tools_or_methods",
        "methods": "tools_or_methods",
        "tools": "tools_or_methods",
        "analysis": "analysis_steps",
        "analysis steps": "analysis_steps",
        "finding": "findings_or_results",
        "findings": "findings_or_results",
        "result": "findings_or_results",
        "results": "findings_or_results",
        "finding/result": "findings_or_results",
        "findings/limitations": "findings_or_results",
        "limitation": "limitations",
        "limitations": "limitations",
        "output": "outputs",
        "outputs": "outputs",
        "context": "collaborators_or_context",
        "collaborators": "collaborators_or_context",
        "role relevance": "role_relevance",
        "skills": "skills_demonstrated",
        "skills demonstrated": "skills_demonstrated",
        "resume bullet claims": "resume_bullet_claims",
        "cover letter angles": "cover_letter_angles",
        "proof artifact angles": "proof_artifact_angles",
        "warnings not to claim": "warnings_not_to_claim",
    }
    _method_terms = (
        ("Gaussian fitting", ("gaussian fit", "gaussian fitting")),
        ("statistical analysis", ("statistical analysis",)),
        ("statistical modeling", ("statistical model", "statistical modeling")),
        ("modeling", ("modeling", "modelling")),
        (
            "uncertainty and error propagation",
            ("uncertainty", "error propagation", "propagated error"),
        ),
        ("data visualization", ("visualization", "visualisation", "plotting")),
        (
            "technical communication",
            ("technical communication", "poster", "presented", "presentation"),
        ),
    )

    def extract(self, text: str, memory_title: str) -> tuple[dict[str, Any], list[str]]:
        cleaned = self._clean(text)
        fields: dict[str, Any] = {}
        labeled = self._labeled_fields(cleaned)
        fields.update(labeled)
        sentences = self._sentences(cleaned)

        fields.setdefault("project_title", memory_title)
        self._set_if_supported(
            fields,
            "research_question",
            sentences,
            ("research question", "investigat", "whether", "tested whether"),
        )
        self._set_if_supported(
            fields,
            "data_or_inputs",
            sentences,
            ("spectral data", "imaging data", "dataset", "observational data"),
        )
        self._set_if_supported(
            fields,
            "analysis_steps",
            sentences,
            (
                "gaussian fit",
                "statistical analysis",
                "modeling",
                "modelling",
                "uncertainty",
                "error propagation",
                "visualization",
            ),
        )
        self._set_if_supported(
            fields,
            "findings_or_results",
            sentences,
            ("no clear trend", "inconclusive", "result", "found", "finding"),
        )
        self._set_if_supported(
            fields,
            "limitations",
            sentences,
            ("limitation", "limited", "no clear trend", "inconclusive"),
        )
        self._set_if_supported(
            fields,
            "outputs",
            sentences,
            ("poster", "report", "presentation", "deliverable", "paper"),
        )
        self._set_if_supported(
            fields,
            "collaborators_or_context",
            [
                sentence
                for sentence in sentences
                if not sentence.casefold().startswith("outputs:")
            ],
            ("honors", "capstone", "collaborat", "mentor", "advisor", "team"),
        )

        folded = cleaned.casefold()
        methods = [
            label
            for label, needles in self._method_terms
            if any(needle in folded for needle in needles)
        ]
        if "statistical modeling" in methods and "modeling" in methods:
            methods.remove("modeling")
        if methods:
            existing = fields.get("tools_or_methods")
            fields["tools_or_methods"] = self._normalized_methods(
                existing, methods
            )
            fields.setdefault(
                "skills_demonstrated", fields["tools_or_methods"]
            )

        fields = self._future_hooks(fields, memory_title)
        warnings = self._warnings(cleaned, fields)
        existing_warnings = fields.get("warnings_not_to_claim")
        fields["warnings_not_to_claim"] = self._as_list(
            existing_warnings, warnings
        )
        useful = [
            key
            for key in fields
            if key not in {"project_title", "warnings_not_to_claim"}
        ]
        if len(cleaned) < 120 or len(useful) < 2:
            warnings.insert(0, PARSE_QUALITY_WARNING)
        return fields, list(dict.fromkeys(warnings))

    @classmethod
    def _future_hooks(
        cls, fields: dict[str, Any], memory_title: str
    ) -> dict[str, Any]:
        question = cls._first(fields.get("research_question")) or cls._first(
            fields.get("project_goal")
        )
        methods = cls._as_list(fields.get("tools_or_methods"), [])
        finding = cls._first(fields.get("findings_or_results"))
        if question and methods and "resume_bullet_claims" not in fields:
            method_text = cls._join(methods[:4])
            direct_question = re.match(
                r"^(?:how|what|why|which|when|where|who)\b", question, re.I
            )
            if direct_question:
                question_text = f"a project question—{question.rstrip('.!?')}—"
                resume_verb = "Explored"
            else:
                question_text = re.sub(
                    r"^(?:investigat(?:e|ed|es|ing)|test(?:ed|s|ing))\s+",
                    "",
                    cls._lower_start(question).rstrip(".!?"),
                    flags=re.I,
                )
                resume_verb = "Investigated"
            fields["resume_bullet_claims"] = [
                f"{resume_verb} {question_text} using {method_text}."
            ]
        if question and "cover_letter_angles" not in fields:
            fields["cover_letter_angles"] = [
                f"Use {memory_title} to explain how a research question was turned "
                "into a documented analytical process."
            ]
        uncertainty_supported = any(
            "uncertainty" in method.casefold()
            or "error propagation" in method.casefold()
            for method in methods
        )
        if "proof_artifact_angles" not in fields and (question or methods):
            evidence_sequence = (
                "problem, inputs, method, uncertainty, and supported finding"
                if uncertainty_supported
                else "problem, inputs, method, and supported finding"
            )
            fields["proof_artifact_angles"] = [
                f"Lead with the {evidence_sequence} so a reviewer does not have "
                "to infer the work."
            ]
        if finding and "role_relevance" not in fields:
            fields["role_relevance"] = (
                "Shows the ability to test a hypothesis, interpret uncertainty, "
                "and communicate a nuanced result."
                if uncertainty_supported
                else "Shows the ability to turn a project question into a documented "
                "method and communicate a supported result."
            )
        if fields.get("role_relevance") and "role_specific_framing" not in fields:
            fields["role_specific_framing"] = fields["role_relevance"]
        if question and methods and "proof_artifact_summary" not in fields:
            summary = (
                f"{memory_title}: {question.rstrip('.!?')}. "
                f"Methods: {cls._join(methods)}."
            )
            if finding:
                summary += f" Finding: {finding.rstrip('.!?')}."
            fields["proof_artifact_summary"] = summary
        return fields

    @staticmethod
    def _warnings(text: str, fields: dict[str, Any]) -> list[str]:
        warnings: list[str] = []
        if not re.search(r"\b\d+(?:\.\d+)?\s*(?:%|percent|x\b)", text, re.I):
            warnings.append(
                "Do not claim quantified impact or performance without additional "
                "approved evidence."
            )
        if not fields.get("findings_or_results"):
            warnings.append(
                "Do not claim a project finding that is not present in this evidence."
            )
        return warnings

    @classmethod
    def _labeled_fields(cls, text: str) -> dict[str, Any]:
        fields: dict[str, Any] = {}
        for line in text.splitlines():
            match = re.match(r"^\s*[-*]?\s*([^:]{2,40}):\s*(.+?)\s*$", line)
            if not match:
                continue
            key = cls._labels.get(match.group(1).casefold().strip())
            if key:
                value = match.group(2).strip()
                current = fields.get(key)
                fields[key] = cls._as_list(current, [value]) if current else value
        return fields

    @staticmethod
    def _clean(text: str) -> str:
        return "\n".join(line.strip() for line in text.splitlines() if line.strip())

    @staticmethod
    def _sentences(text: str) -> list[str]:
        return [
            item.strip(" -*\t")
            for item in re.split(r"(?<=[.!?])\s+|\n+", text)
            if len(item.strip(" -*\t")) >= 12
        ]

    @staticmethod
    def _set_if_supported(
        fields: dict[str, Any], key: str, sentences: list[str], needles: tuple[str, ...]
    ) -> None:
        if key in fields:
            return
        matches = [
            re.sub(r"^[^:]{2,40}:\s*", "", sentence).strip()
            for sentence in sentences
            if any(needle in sentence.casefold() for needle in needles)
        ]
        if matches:
            fields[key] = matches[0] if len(matches) == 1 else matches[:4]

    @staticmethod
    def _first(value: Any) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, list):
            return next(
                (str(item).strip() for item in value if str(item).strip()), None
            )
        return None

    @staticmethod
    def _as_list(value: Any, additional: list[str]) -> list[str]:
        current = value if isinstance(value, list) else [value] if value else []
        return list(
            dict.fromkeys(
                str(item).strip()
                for item in [*current, *additional]
                if str(item).strip()
            )
        )

    @classmethod
    def _normalized_methods(cls, value: Any, supported: list[str]) -> list[str]:
        current = value if isinstance(value, list) else [value] if value else []
        explicit = [
            item.strip(" .")
            for entry in current
            for item in re.split(r"[,;]", str(entry))
            if item.strip(" .")
        ]
        canonical: list[str] = []
        for item in explicit:
            folded = item.casefold()
            match = next(
                (
                    label
                    for label, needles in cls._method_terms
                    if any(needle in folded for needle in needles)
                ),
                item,
            )
            if match.casefold() not in {value.casefold() for value in canonical}:
                canonical.append(match)
        for item in supported:
            if item.casefold() not in {value.casefold() for value in canonical}:
                canonical.append(item)
        return canonical

    @staticmethod
    def _join(values: list[str]) -> str:
        if len(values) == 1:
            return values[0]
        if len(values) == 2:
            return " and ".join(values)
        return f"{', '.join(values[:-1])}, and {values[-1]}"

    @staticmethod
    def _lower_start(value: str) -> str:
        return value[0].lower() + value[1:] if value else value


class CareerMemoryEnrichmentService:
    """Manage enrichment review while keeping canonical mutation approval-gated."""

    _projection_keys = {
        "project_goal": "enriched_problem",
        "research_question": "enriched_problem",
        "data_or_inputs": "enriched_data_or_inputs",
        "tools_or_methods": "enriched_method",
        "analysis_steps": "enriched_method",
        "findings_or_results": "enriched_findings",
        "limitations": "enriched_limitations",
        "outputs": "enriched_outputs",
        "collaborators_or_context": "enriched_context",
        "role_relevance": "enriched_role_relevance",
        "role_specific_framing": "enriched_role_specific_framing",
        "skills_demonstrated": "enriched_skills",
        "resume_bullet_claims": "enriched_resume_bullets",
        "cover_letter_angles": "enriched_cover_letter_angles",
        "proof_artifact_angles": "enriched_proof_artifact_angles",
        "proof_artifact_summary": "enriched_proof_artifact_summary",
        "warnings_not_to_claim": "warnings_not_to_claim",
    }

    def __init__(
        self,
        user_id: uuid.UUID = DEMO_USER_ID,
        extractor: ProjectEnrichmentExtractor | None = None,
    ) -> None:
        self.user_id = user_id
        self.extractor = extractor or ProjectEnrichmentExtractor()

    def create(
        self,
        session: Session,
        memory_id: uuid.UUID,
        request: EnrichmentCreateRequest,
    ) -> EnrichmentView:
        memory = self._approved_memory(session, memory_id)
        text, source, evidence_ids = self._source_material(session, request)
        structured, warnings = self.extractor.extract(text, memory.title)
        resolution = self._explicit_resolution(memory, evidence_ids)
        existing = session.scalar(
            select(CareerMemoryEnrichment).where(
                CareerMemoryEnrichment.user_id == self.user_id,
                CareerMemoryEnrichment.canonical_memory_id == memory.id,
                CareerMemoryEnrichment.status == EnrichmentStatus.PROPOSED.value,
                CareerMemoryEnrichment.structured_enrichment == structured,
            )
        )
        if existing is not None:
            self._attach_supporting_evidence(
                existing,
                evidence_ids=evidence_ids,
                source_id=source.id if source else request.source_id,
                source_label=(
                    request.source_label or (source.label if source else None)
                ),
            )
            session.commit()
            session.refresh(existing)
            return self._view(existing, memory)
        record = CareerMemoryEnrichment(
            user_id=self.user_id,
            canonical_memory_id=memory.id,
            source_id=source.id if source else request.source_id,
            source_label=(
                request.source_label
                or (source.label if source else "Pasted project detail")
            ),
            status=EnrichmentStatus.PROPOSED.value,
            enrichment_type=request.enrichment_type.value,
            structured_enrichment=structured,
            evidence_ids=evidence_ids,
            confidence=Decimal(
                "0.92" if PARSE_QUALITY_WARNING not in warnings else "0.58"
            ),
            reasoning=(
                f"The user explicitly attached this evidence to {memory.title}; "
                "approval is still required before CareerOS uses it."
            ),
            identity_resolution=resolution.model_dump(mode="json"),
            warnings=warnings,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return self._view(record, memory)

    def create_from_proposal(
        self,
        session: Session,
        memory: CanonicalMemoryRecord,
        proposal: KnowledgeProposal,
        resolution: MemoryIdentityResolution,
    ) -> CareerMemoryEnrichment:
        evidence_ids = [
            str(item.evidence_id)
            for item in proposal.evidence
            if item.evidence_id is not None
        ]
        text = self._proposal_source_text(proposal)
        structured, warnings = self.extractor.extract(text, memory.title)
        existing = session.scalar(
            select(CareerMemoryEnrichment).where(
                CareerMemoryEnrichment.user_id == self.user_id,
                CareerMemoryEnrichment.canonical_memory_id == memory.id,
                CareerMemoryEnrichment.status == EnrichmentStatus.PROPOSED.value,
                CareerMemoryEnrichment.structured_enrichment == structured,
            )
        )
        if existing is not None:
            self._attach_supporting_evidence(
                existing,
                evidence_ids=evidence_ids,
                source_id=self._first_uuid(
                    item.source_id for item in proposal.evidence
                ),
                source_label=(
                    proposal.source_names[0] if proposal.source_names else None
                ),
            )
            return existing
        source_id = self._first_uuid(item.source_id for item in proposal.evidence)
        record = CareerMemoryEnrichment(
            user_id=self.user_id,
            canonical_memory_id=memory.id,
            source_id=source_id,
            source_label=(proposal.source_names[0] if proposal.source_names else None),
            status=EnrichmentStatus.PROPOSED.value,
            enrichment_type=EnrichmentType.PROJECT_FULL_ENRICHMENT.value,
            structured_enrichment=structured,
            evidence_ids=evidence_ids,
            confidence=Decimal(str(resolution.confidence)),
            reasoning=(
                f"CareerOS matched the project evidence to {memory.title} and "
                "created an enrichment proposal instead of a duplicate memory."
            ),
            identity_resolution=resolution.model_dump(mode="json"),
            warnings=warnings,
        )
        session.add(record)
        return record

    @staticmethod
    def _proposal_source_text(proposal: KnowledgeProposal) -> str:
        """Prefer verbatim evidence over serialized proposal metadata.

        Proposal dictionaries contain dates, parser keys, and sometimes a summary
        assembled from several excerpts. Feeding their JSON representation back
        through the extractor can turn that syntax into apparent project facts.
        The evidence excerpts are the authoritative source for enrichment.
        """

        excerpts = list(
            dict.fromkeys(
                item.excerpt.strip()
                for item in proposal.evidence
                if item.excerpt.strip()
            )
        )
        if excerpts:
            return "\n".join(excerpts)

        labels = {
            "summary": "Project goal",
            "objective": "Project goal",
            "research_question": "Research question",
            "data_or_inputs": "Data or inputs",
            "methods": "Methods",
            "tools_or_methods": "Methods",
            "findings": "Findings",
            "findings_or_results": "Findings",
            "limitations": "Limitations",
            "outputs": "Outputs",
        }
        lines: list[str] = []
        for key, label in labels.items():
            value = proposal.proposed_value.get(key)
            values = value if isinstance(value, list) else [value]
            supported = [
                str(item).strip()
                for item in values
                if isinstance(item, (str, int, float)) and str(item).strip()
            ]
            if supported:
                lines.append(f"{label}: {'; '.join(supported)}")
        fallback_title = next(
            (
                str(proposal.proposed_value.get(key)).strip()
                for key in ("title", "name", "project_name")
                if proposal.proposed_value.get(key)
            ),
            "Project evidence",
        )
        return "\n".join(lines) or fallback_title

    @staticmethod
    def _attach_supporting_evidence(
        record: CareerMemoryEnrichment,
        *,
        evidence_ids: list[str],
        source_id: uuid.UUID | None,
        source_label: str | None,
    ) -> None:
        record.evidence_ids = list(
            dict.fromkeys([*record.evidence_ids, *evidence_ids])
        )
        identity_resolution = dict(record.identity_resolution)
        identity_resolution["evidence_ids"] = list(
            dict.fromkeys(
                [*identity_resolution.get("evidence_ids", []), *evidence_ids]
            )
        )
        record.identity_resolution = identity_resolution
        if record.source_id is None and source_id is not None:
            record.source_id = source_id
        if source_label and record.source_label != source_label:
            record.source_label = " | ".join(
                dict.fromkeys(
                    label
                    for label in (record.source_label, source_label)
                    if label
                )
            )

    def convert_proposal(
        self,
        session: Session,
        memory_id: uuid.UUID,
        proposal_id: str,
    ) -> EnrichmentView:
        memory = self._approved_memory(session, memory_id)
        proposal_record = session.scalar(
            select(ReviewProposal).where(
                ReviewProposal.id == proposal_id,
                ReviewProposal.user_id == self.user_id,
            )
        )
        if proposal_record is None:
            raise EnrichmentNotFoundError("Review proposal not found.")
        if proposal_record.proposal_type != "PROJECT":
            raise EnrichmentStateError(
                "Only a project proposal can be converted to project enrichment."
            )
        proposal = KnowledgeProposal.model_validate(proposal_record.proposal_data)
        resolution = MemoryIdentityResolution(
            resolution=MemoryResolutionKind.ENRICH_EXISTING,
            confidence=1.0,
            matched_memory_id=memory.id,
            matched_memory_title=memory.title,
            matched_proposal_id=proposal_record.id,
            reasons=[
                "The user attached this duplicate project draft to an approved memory."
            ],
            evidence_ids=[
                str(item.evidence_id)
                for item in proposal.evidence
                if item.evidence_id is not None
            ],
            recommended_review_action=RecommendedReviewAction.CREATE_ENRICHMENT,
        )
        record = self.create_from_proposal(session, memory, proposal, resolution)
        proposal_record.decision = DurableReviewStatus.REJECTED.value
        proposal_record.proposal_data = proposal.model_copy(
            update={"approval_state": ApprovalState.REJECTED}
        ).model_dump(mode="json")
        session.commit()
        session.refresh(record)
        return self._view(record, memory)

    def list(
        self, session: Session, memory_id: uuid.UUID | None = None
    ) -> list[EnrichmentView]:
        statement = select(CareerMemoryEnrichment).where(
            CareerMemoryEnrichment.user_id == self.user_id
        )
        if memory_id is not None:
            self._memory(session, memory_id)
            statement = statement.where(
                CareerMemoryEnrichment.canonical_memory_id == memory_id
            )
        records = session.scalars(
            statement.order_by(CareerMemoryEnrichment.created_at.desc())
        ).all()
        memories = {
            memory.id: memory
            for memory in session.scalars(
                select(CanonicalMemoryRecord).where(
                    CanonicalMemoryRecord.id.in_(
                        [record.canonical_memory_id for record in records]
                    ),
                    CanonicalMemoryRecord.user_id == self.user_id,
                )
            ).all()
        }
        return [
            self._view(record, memories[record.canonical_memory_id])
            for record in records
            if record.canonical_memory_id in memories
        ]

    def update(
        self,
        session: Session,
        enrichment_id: uuid.UUID,
        request: EnrichmentUpdateRequest,
    ) -> EnrichmentView:
        record = self._get(session, enrichment_id)
        memory = self._memory(session, record.canonical_memory_id)
        if request.structured_enrichment is not None:
            record.structured_enrichment = request.structured_enrichment
        if request.reasoning is not None:
            record.reasoning = request.reasoning
        if request.status is not None:
            if request.status is EnrichmentStatus.APPROVED:
                self._assert_memory_approved(session, memory)
            record.status = request.status.value
        session.flush()
        self._rebuild_projection(session, memory)
        session.commit()
        session.refresh(record)
        return self._view(record, memory)

    def _source_material(
        self, session: Session, request: EnrichmentCreateRequest
    ) -> tuple[str, ListeningSource | None, list[str]]:
        source: ListeningSource | None = None
        parts = [request.enrichment_text or ""]
        if request.source_id is not None:
            source = session.scalar(
                select(ListeningSource).where(
                    ListeningSource.id == request.source_id,
                    ListeningSource.user_id == self.user_id,
                )
            )
            if source is None:
                raise EnrichmentNotFoundError("Project source not found.")
            parts.append(source.raw_text)
        statement = select(ListeningEvidence).where(
            ListeningEvidence.user_id == self.user_id
        )
        if request.evidence_ids:
            statement = statement.where(ListeningEvidence.id.in_(request.evidence_ids))
        elif source is not None:
            statement = statement.where(ListeningEvidence.source_id == source.id)
        else:
            statement = statement.where(False)
        evidence = session.scalars(statement).all()
        if request.evidence_ids and len(evidence) != len(set(request.evidence_ids)):
            raise EnrichmentNotFoundError(
                "One or more evidence references were unavailable."
            )
        parts.extend(item.raw_excerpt for item in evidence)
        return (
            "\n".join(part for part in parts if part.strip()),
            source,
            [str(item.id) for item in evidence],
        )

    def _rebuild_projection(
        self, session: Session, memory: CanonicalMemoryRecord
    ) -> None:
        current = dict(memory.structured_fields)
        base_evidence = list(
            current.get("_enrichment_base_evidence_ids", memory.evidence_ids)
        )
        base_sources = list(
            current.get("_enrichment_base_source_ids", memory.source_ids)
        )
        base_warnings = current.get(
            "_enrichment_base_warnings_not_to_claim",
            current.get("warnings_not_to_claim", []),
        )
        fields = {
            key: value
            for key, value in current.items()
            if not key.startswith("enriched_")
            and key
            not in {
                "warnings_not_to_claim",
                "approved_enrichment_ids",
                "_enrichment_base_evidence_ids",
                "_enrichment_base_source_ids",
                "_enrichment_base_warnings_not_to_claim",
            }
        }
        fields["_enrichment_base_evidence_ids"] = base_evidence
        fields["_enrichment_base_source_ids"] = base_sources
        fields["_enrichment_base_warnings_not_to_claim"] = base_warnings
        if base_warnings:
            fields["warnings_not_to_claim"] = base_warnings
        approved = session.scalars(
            select(CareerMemoryEnrichment)
            .where(
                CareerMemoryEnrichment.user_id == self.user_id,
                CareerMemoryEnrichment.canonical_memory_id == memory.id,
                CareerMemoryEnrichment.status == EnrichmentStatus.APPROVED.value,
            )
            .order_by(CareerMemoryEnrichment.created_at)
        ).all()
        evidence_ids = list(base_evidence)
        source_ids = list(base_sources)
        for enrichment in approved:
            for source_key, target_key in self._projection_keys.items():
                value = enrichment.structured_enrichment.get(source_key)
                if value is not None:
                    fields[target_key] = self._merge_value(
                        fields.get(target_key), value
                    )
            evidence_ids.extend(enrichment.evidence_ids)
            if enrichment.source_id is not None:
                source_ids.append(str(enrichment.source_id))
        if approved:
            fields["approved_enrichment_ids"] = [str(item.id) for item in approved]
        memory.structured_fields = fields
        memory.evidence_ids = list(dict.fromkeys(evidence_ids))
        memory.source_ids = list(dict.fromkeys(source_ids))

    @staticmethod
    def _merge_value(existing: Any, incoming: Any) -> Any:
        existing_values = (
            existing
            if isinstance(existing, list)
            else [existing]
            if existing
            else []
        )
        incoming_values = incoming if isinstance(incoming, list) else [incoming]
        merged = list(
            dict.fromkeys(
                json.dumps(item, sort_keys=True, default=str)
                for item in [*existing_values, *incoming_values]
                if item not in (None, "", [])
            )
        )
        values = [json.loads(item) for item in merged]
        return values[0] if len(values) == 1 else values

    def _approved_memory(
        self, session: Session, memory_id: uuid.UUID
    ) -> CanonicalMemoryRecord:
        memory = self._memory(session, memory_id)
        if memory.memory_type != "PROJECT":
            raise EnrichmentStateError(
                "Only approved project Career Memory can receive project enrichment."
            )
        self._assert_memory_approved(session, memory)
        return memory

    def _assert_memory_approved(
        self, session: Session, memory: CanonicalMemoryRecord
    ) -> None:
        decision = session.scalar(
            select(ReviewProposal.decision).where(
                ReviewProposal.id == memory.review_proposal_id,
                ReviewProposal.user_id == self.user_id,
            )
        )
        if decision not in {
            DurableReviewStatus.APPROVED.value,
            DurableReviewStatus.EDITED_APPROVED.value,
        }:
            raise EnrichmentStateError(
                "Only approved canonical Career Memory can be enriched."
            )

    def _memory(
        self, session: Session, memory_id: uuid.UUID
    ) -> CanonicalMemoryRecord:
        memory = session.scalar(
            select(CanonicalMemoryRecord).where(
                CanonicalMemoryRecord.id == memory_id,
                CanonicalMemoryRecord.user_id == self.user_id,
            )
        )
        if memory is None:
            raise EnrichmentNotFoundError("Career Memory not found.")
        return memory

    def _get(
        self, session: Session, enrichment_id: uuid.UUID
    ) -> CareerMemoryEnrichment:
        record = session.scalar(
            select(CareerMemoryEnrichment).where(
                CareerMemoryEnrichment.id == enrichment_id,
                CareerMemoryEnrichment.user_id == self.user_id,
            )
        )
        if record is None:
            raise EnrichmentNotFoundError("Memory enrichment not found.")
        return record

    @staticmethod
    def _explicit_resolution(
        memory: CanonicalMemoryRecord, evidence_ids: list[str]
    ) -> MemoryIdentityResolution:
        return MemoryIdentityResolution(
            resolution=MemoryResolutionKind.ENRICH_EXISTING,
            confidence=1.0,
            matched_memory_id=memory.id,
            matched_memory_title=memory.title,
            reasons=["The user explicitly selected this approved Career Memory."],
            evidence_ids=evidence_ids,
            recommended_review_action=RecommendedReviewAction.CREATE_ENRICHMENT,
        )

    @staticmethod
    def _first_uuid(values: Any) -> uuid.UUID | None:
        for value in values:
            try:
                return uuid.UUID(str(value))
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _readiness_impact(fields: dict[str, Any]) -> str:
        covered = [
            key
            for key in (
                "research_question",
                "data_or_inputs",
                "tools_or_methods",
                "analysis_steps",
                "findings_or_results",
                "limitations",
                "outputs",
            )
            if fields.get(key)
        ]
        if len(covered) >= 5:
            return "Adds strong project detail for regenerated proof artifacts."
        if len(covered) >= 2:
            return "Adds useful project detail, with some proof sections still thin."
        return "Needs more project-specific text before proof readiness improves."

    def _view(
        self,
        record: CareerMemoryEnrichment,
        memory: CanonicalMemoryRecord,
    ) -> EnrichmentView:
        return EnrichmentView(
            id=record.id,
            target_memory=CareerMemoryTarget(
                id=memory.id,
                title=memory.title,
                memory_type=memory.memory_type,
            ),
            status=EnrichmentStatus(record.status),
            enrichment_type=EnrichmentType(record.enrichment_type),
            structured_enrichment=record.structured_enrichment,
            evidence_ids=record.evidence_ids,
            source_id=record.source_id,
            source_label=record.source_label,
            confidence=float(record.confidence),
            reasoning=record.reasoning,
            identity_resolution=MemoryIdentityResolution.model_validate(
                record.identity_resolution
            ),
            warnings=record.warnings,
            proof_artifact_readiness_impact=self._readiness_impact(
                record.structured_enrichment
            ),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
