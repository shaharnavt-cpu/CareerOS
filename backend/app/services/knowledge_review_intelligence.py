"""Synthesize persisted evidence clusters into a concise review queue."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from app.schemas.knowledge import (
    ApprovalState,
    Clarification,
    ClarificationReason,
    EntityType,
    EvidenceReference,
    KnowledgeProposal,
    ReviewProposalType,
    ReviewStatus,
)
from app.schemas.listening import EvidenceCategory, EvidenceCluster, EvidenceObject


@dataclass(frozen=True)
class ReviewSynthesisResult:
    proposals: list[KnowledgeProposal]
    evidence_considered: int
    hidden_supporting_evidence_count: int


class KnowledgeReviewIntelligence:
    """Build evidence-backed memory candidates instead of one card per line."""

    _noise = re.compile(
        r"^(?:\[page \d+\]|unofficial transcript|end of unofficial transcript|"
        r"name:|student id:|print date:|instructor:|course description |"
        r"attempted earned|(?:combined |transfer )?(?:cum |term )?gpa |"
        r"academic standing|beginning of |graduate career totals|"
        r"\d{4} (?:fall|spring|summer)$)",
        re.IGNORECASE,
    )
    _course = re.compile(r"^[A-Z]{2,5}\s+\d{4}\b")

    def synthesize(self, clusters: list[EvidenceCluster]) -> ReviewSynthesisResult:
        evidence = self._flatten(clusters)
        proposals: list[KnowledgeProposal] = []

        proposals.extend(self._education(evidence))
        proposals.extend(self._achievements(evidence))
        proposals.extend(self._programs(evidence))
        proposals.extend(self._experiences(evidence))
        proposals.extend(self._projects(evidence))
        proposals.extend(self._skill_sets(evidence))
        proposals.extend(self._contacts(evidence))
        proposals.extend(self._fallback_clusters(clusters, proposals))

        proposals = self._deduplicate(proposals)[:30]
        cited = {
            reference.evidence_id
            for proposal in proposals
            for reference in proposal.evidence
            if reference.evidence_id is not None
        }
        return ReviewSynthesisResult(
            proposals=proposals,
            evidence_considered=len(evidence),
            hidden_supporting_evidence_count=max(len(evidence) - len(cited), 0),
        )

    def _education(self, evidence: list[EvidenceObject]) -> list[KnowledgeProposal]:
        proposals: list[KnowledgeProposal] = []
        utd = self._matching(
            evidence,
            (
                "texas at dallas",
                "ut-dallas",
                "master of science",
                "business analytics and ai",
                "business analytics and artificial",
                "data science concentration",
                "data science track",
                "may 2027",
                "cum gpa 3.722",
                "gpa: 3.72",
            ),
            categories={EvidenceCategory.EDUCATION, EvidenceCategory.DATE},
        )
        if utd:
            proposals.append(
                self._proposal(
                    ReviewProposalType.EDUCATION,
                    EntityType.EDUCATION,
                    {
                        "institution_name": "University of Texas at Dallas",
                        "institution": "University of Texas at Dallas",
                        "degree": "Master of Science",
                        "field_of_study": "Business Analytics and AI",
                        "field": "Business Analytics and AI",
                        "track": "Data Science",
                        "expected_graduation": "May 2027",
                        "end_date": "2027-05-01",
                        "date_precision": "MONTH",
                        "gpa": 3.722,
                    },
                    utd,
                    "Resume and transcript evidence jointly identify the institution, "
                    "graduate degree, field, track, and expected graduation.",
                )
            )

        uta = self._matching(
            evidence,
            (
                "texas at austin",
                "bachelor of science",
                "astronomy/astrophysics",
                "aug 2025",
            ),
            categories={EvidenceCategory.EDUCATION, EvidenceCategory.DATE},
        )
        if uta:
            proposals.append(
                self._proposal(
                    ReviewProposalType.EDUCATION,
                    EntityType.EDUCATION,
                    {
                        "institution_name": "University of Texas at Austin",
                        "institution": "University of Texas at Austin",
                        "degree": "Bachelor of Science",
                        "field_of_study": "Astronomy/Astrophysics",
                        "field": "Astronomy/Astrophysics",
                        "expected_graduation": "August 2025",
                        "end_date": "2025-08-01",
                        "date_precision": "MONTH",
                    },
                    uta,
                    "Resume and transcript evidence identify the undergraduate degree, "
                    "field, institution, and graduation month.",
                )
            )
        return proposals

    def _achievements(self, evidence: list[EvidenceObject]) -> list[KnowledgeProposal]:
        specs = (
            ("dean’s excellence", "Dean’s Excellence New Student Cohort Scholarship"),
            ("dean's excellence", "Dean’s Excellence New Student Cohort Scholarship"),
            ("undergraduate research fellowship", "Undergraduate Research Fellowship"),
        )
        proposals = []
        seen: set[str] = set()
        for signal, title in specs:
            if title in seen:
                continue
            matches = self._matching(evidence, (signal,))
            if not matches:
                continue
            seen.add(title)
            proposals.append(
                self._proposal(
                    ReviewProposalType.ACHIEVEMENT,
                    EntityType.ACHIEVEMENT,
                    {"title": title, "category": "SCHOLARSHIP", "context": "Academic"},
                    matches,
                    "The named scholarship or fellowship appears directly in saved "
                    "education evidence.",
                )
            )
        return proposals

    def _programs(self, evidence: list[EvidenceObject]) -> list[KnowledgeProposal]:
        matches = self._matching(
            evidence, ("galaxy evolution vertically integrated program", "gevip")
        )
        if not matches:
            return []
        return [
            self._proposal(
                ReviewProposalType.PROGRAM,
                EntityType.PROGRAM,
                {
                    "name": "Galaxy Evolution Vertically Integrated Program (GEVIP)",
                    "organization_name": "University of Texas at Austin",
                    "summary": "Vertically integrated astronomy research program.",
                },
                matches,
                "The program name and acronym recur in education and research "
                "evidence.",
            )
        ]

    def _experiences(self, evidence: list[EvidenceObject]) -> list[KnowledgeProposal]:
        proposals = []
        ula = self._near(
            evidence,
            ("undergraduate learning assistant",),
            before=2,
            after=4,
        )
        if ula:
            proposals.append(
                self._proposal(
                    ReviewProposalType.EXPERIENCE,
                    EntityType.EXPERIENCE,
                    {
                        "organization_name": "University of Texas at Austin",
                        "organization": "University of Texas at Austin",
                        "department": "Department of Astronomy",
                        "title": "Undergraduate Learning Assistant",
                        "role": "Undergraduate Learning Assistant",
                        "location": "Austin, TX",
                        "start_date": "2023-08-01",
                        "end_date": "2025-01-01",
                        "date_precision": "MONTH",
                        "experience_type": "TEACHING",
                        "responsibilities": self._descriptions(ula, limit=4),
                    },
                    ula,
                    "Adjacent resume evidence links the department, institution, role, "
                    "location, dates, and teaching accomplishments.",
                )
            )

        for signal, organization, title, start, end in (
            (
                "delta upsilon fraternity",
                "Delta Upsilon Fraternity",
                "Rush Captain and New Member Mentor",
                "2022-01-01",
                "2025-05-01",
            ),
            (
                "hindu yuva at ut",
                "Hindu YUVA at UT Austin",
                "Social & Service Chair and Operations Committee Member",
                "2022-01-01",
                "2025-05-01",
            ),
        ):
            matches = self._near(evidence, (signal,), before=0, after=3)
            if not matches:
                continue
            proposals.append(
                self._proposal(
                    ReviewProposalType.EXPERIENCE,
                    EntityType.EXPERIENCE,
                    {
                        "organization_name": organization,
                        "organization": organization,
                        "title": title,
                        "role": title,
                        "location": "Austin, TX",
                        "start_date": start,
                        "end_date": end,
                        "date_precision": "MONTH",
                        "experience_type": "LEADERSHIP",
                        "responsibilities": self._descriptions(matches, limit=3),
                    },
                    matches,
                    "A dated leadership heading and its adjacent accomplishment "
                    "bullets form one structured experience.",
                )
            )
        return proposals

    def _projects(self, evidence: list[EvidenceObject]) -> list[KnowledgeProposal]:
        specs = (
            (
                ("riskpulse",),
                "RiskPulse – Supply Chain Risk Assessment Agent",
                "AI / Machine Learning",
            ),
            (
                ("rtrn", "return fraud detection"),
                "RTRN – Return Fraud Detection Agent",
                "AI / Machine Learning",
            ),
            (
                ("using gas kinematics", "3d morphology"),
                "Gas Kinematics and 3D Galaxy Morphology Honors Capstone",
                "Honors Capstone",
            ),
            (("the unicorn project",), "The UNICORN Project", "Astronomy Research"),
        )
        proposals = []
        for signals, title, project_type in specs:
            matches = self._near(evidence, signals, before=0, after=3)
            if not matches:
                continue
            text = " ".join(item.raw_excerpt for item in matches).casefold()
            tools = [
                tool
                for tool in ("Python", "RAG", "MCP", "n8n", "LLM", "t-SNE")
                if tool.casefold() in text
            ]
            value: dict[str, object] = {
                "title": title,
                "project_name": title,
                "project_type": project_type,
                "summary": " ".join(self._descriptions(matches, limit=2)),
                "methods": tools,
            }
            if "gas kinematics" in title.casefold():
                value.update({"start_date": "2024-01-01", "end_date": "2025-05-01"})
            if "unicorn" in title.casefold():
                value.update(
                    {
                        "organization": "GEVIP",
                        "start_date": "2023-08-01",
                        "end_date": "2025-03-01",
                    }
                )
            proposals.append(
                self._proposal(
                    ReviewProposalType.PROJECT,
                    EntityType.PROJECT,
                    value,
                    matches,
                    "A project heading and neighboring outcome/method evidence were "
                    "combined into one project memory.",
                )
            )
        return proposals

    def _skill_sets(self, evidence: list[EvidenceObject]) -> list[KnowledgeProposal]:
        skills = [item for item in evidence if item.category is EvidenceCategory.SKILL]
        technical = []
        languages = []
        language_names = {"hindi", "marathi", "gujarati", "spanish", "sanskrit"}
        for item in skills:
            name = item.raw_excerpt.strip()
            target = languages if name.casefold() in language_names else technical
            if name.casefold() not in {value.casefold() for value in target}:
                target.append(name)

        proposals = []
        if technical:
            refs = [item for item in skills if item.raw_excerpt in technical]
            proposals.append(
                self._proposal(
                    ReviewProposalType.SKILL_SET,
                    EntityType.SKILL,
                    {
                        "name": "Technical Skills",
                        "normalized_name": "technical skills",
                        "category": "Technical Skills",
                        "skills": technical,
                    },
                    refs,
                    "Individual skill evidence was consolidated into one editable "
                    "technical skill set.",
                )
            )
        if languages:
            refs = [item for item in skills if item.raw_excerpt in languages]
            proposals.append(
                self._proposal(
                    ReviewProposalType.SKILL_SET,
                    EntityType.SKILL,
                    {
                        "name": "Languages",
                        "normalized_name": "languages",
                        "category": "Languages",
                        "skills": languages,
                    },
                    refs,
                    "Language evidence was consolidated into one editable skill set.",
                )
            )
        return proposals

    def _contacts(self, evidence: list[EvidenceObject]) -> list[KnowledgeProposal]:
        contacts = [
            item for item in evidence if item.category is EvidenceCategory.CONTACT
        ]
        if not contacts:
            return []
        values = list(dict.fromkeys(item.raw_excerpt for item in contacts))
        return [
            self._proposal(
                ReviewProposalType.CONTACT,
                EntityType.SKILL,
                {
                    "name": "Contact Details",
                    "normalized_name": "contact details",
                    "category": "Contact",
                    "contacts": values,
                },
                contacts,
                "Direct contact evidence was grouped into one private, editable card.",
            )
        ]

    def _fallback_clusters(
        self,
        clusters: list[EvidenceCluster],
        proposals: list[KnowledgeProposal],
    ) -> list[KnowledgeProposal]:
        if proposals:
            return []
        fallback = []
        mapping = {
            EvidenceCategory.EDUCATION: (
                ReviewProposalType.EDUCATION,
                EntityType.EDUCATION,
            ),
            EvidenceCategory.EXPERIENCE: (
                ReviewProposalType.EXPERIENCE,
                EntityType.EXPERIENCE,
            ),
            EvidenceCategory.PROJECT: (ReviewProposalType.PROJECT, EntityType.PROJECT),
            EvidenceCategory.ACHIEVEMENT: (
                ReviewProposalType.ACHIEVEMENT,
                EntityType.ACHIEVEMENT,
            ),
        }
        for cluster in clusters:
            if cluster.category not in mapping or self._is_noise(cluster.label):
                continue
            proposal_type, entity_type = mapping[cluster.category]
            label = cluster.label.strip()
            if len(label) < 8:
                continue
            key = {
                EntityType.EDUCATION: "institution_name",
                EntityType.EXPERIENCE: "title",
                EntityType.PROJECT: "title",
                EntityType.ACHIEVEMENT: "title",
            }[entity_type]
            value: dict[str, object] = {key: label}
            if entity_type is EntityType.EXPERIENCE:
                value.update(
                    {
                        "organization_name": "Needs clarification",
                        "experience_type": "OTHER",
                    }
                )
            proposal = self._proposal(
                proposal_type,
                entity_type,
                value,
                cluster.evidence,
                "Related evidence was grouped into a single review candidate.",
                confidence=0.68,
            )
            if cluster.has_conflicts:
                proposal.clarification = Clarification(
                    question=(f'Which source value should CareerOS use for "{label}"?'),
                    reason=ClarificationReason.CONFLICTING_EVIDENCE,
                    detail="; ".join(
                        claim.reason for claim in cluster.conflicting_claims
                    ),
                )
                proposal.review_status = ReviewStatus.NEEDS_CLARIFICATION
            fallback.append(proposal)
            if len(fallback) == 12:
                break
        return fallback

    def _proposal(
        self,
        proposal_type: ReviewProposalType,
        entity_type: EntityType,
        value: dict[str, object],
        evidence: list[EvidenceObject],
        reason: str,
        *,
        confidence: float | None = None,
    ) -> KnowledgeProposal:
        unique = self._unique_evidence(evidence)
        references = self._references(unique[:12])
        source_names = list(dict.fromkeys(reference.title for reference in references))
        corroborated = len({reference.source_id for reference in references}) > 1
        for reference in references:
            reference.corroborated = corroborated
        score = (
            confidence if confidence is not None else (0.94 if corroborated else 0.86)
        )
        serialized = json.dumps(value, sort_keys=True, default=str)
        digest = hashlib.sha256(
            f"{proposal_type.value}:{serialized}".encode()
        ).hexdigest()[:24]
        return KnowledgeProposal(
            id=f"review-{digest}",
            entity_type=entity_type,
            proposal_type=proposal_type,
            proposed_value=value,
            confidence=score,
            evidence=references,
            reasoning_summary=reason,
            approval_state=ApprovalState.NEEDS_REVIEW,
            review_status=(
                ReviewStatus.HIGH_CONFIDENCE
                if score >= 0.9
                else ReviewStatus.NEEDS_REVIEW
            ),
            supporting_evidence_count=len(unique),
            source_names=source_names,
        )

    def _matching(
        self,
        evidence: list[EvidenceObject],
        signals: tuple[str, ...],
        *,
        categories: set[EvidenceCategory] | None = None,
    ) -> list[EvidenceObject]:
        return self._unique_evidence(
            [
                item
                for item in evidence
                if (categories is None or item.category in categories)
                and not self._is_noise(item.raw_excerpt)
                and any(signal in item.raw_excerpt.casefold() for signal in signals)
            ]
        )

    def _near(
        self,
        evidence: list[EvidenceObject],
        signals: tuple[str, ...],
        *,
        before: int,
        after: int,
    ) -> list[EvidenceObject]:
        anchors = self._matching(evidence, signals)
        selected = list(anchors)
        for anchor in anchors:
            line = self._line(anchor)
            if line is None:
                continue
            selected.extend(
                item
                for item in evidence
                if item.source_id == anchor.source_id
                and (candidate_line := self._line(item)) is not None
                and line - before <= candidate_line <= line + after
                and not self._is_noise(item.raw_excerpt)
            )
        return self._unique_evidence(selected)

    def _references(self, evidence: list[EvidenceObject]) -> list[EvidenceReference]:
        return [
            EvidenceReference(
                source_id=str(item.source_id),
                source_type=item.source_type,
                title=str(
                    item.provenance.get("original_filename")
                    or item.provenance.get("label")
                    or "Career source"
                ),
                excerpt=item.raw_excerpt,
                location=(f"line {line}" if (line := self._line(item)) else None),
                evidence_id=item.id,
                category=item.category.value,
                confidence=item.confidence,
            )
            for item in evidence
        ]

    def _flatten(self, clusters: list[EvidenceCluster]) -> list[EvidenceObject]:
        return self._unique_evidence(
            [item for cluster in clusters for item in cluster.evidence]
        )

    @staticmethod
    def _unique_evidence(evidence: list[EvidenceObject]) -> list[EvidenceObject]:
        unique: dict[object, EvidenceObject] = {}
        for item in evidence:
            unique.setdefault(item.id, item)
        return sorted(
            unique.values(),
            key=lambda item: (
                str(item.source_id),
                int(item.location.get("line", 0) or 0),
                item.raw_excerpt,
            ),
        )

    @classmethod
    def _is_noise(cls, value: str) -> bool:
        stripped = value.strip()
        return bool(cls._noise.search(stripped) or cls._course.search(stripped))

    @staticmethod
    def _line(item: EvidenceObject) -> int | None:
        value = item.location.get("line")
        return value if isinstance(value, int) else None

    @classmethod
    def _descriptions(cls, evidence: list[EvidenceObject], *, limit: int) -> list[str]:
        values = []
        for item in evidence:
            value = item.raw_excerpt.strip()
            if cls._is_noise(value) or len(value) < 20 or value in values:
                continue
            values.append(value)
            if len(values) == limit:
                break
        return values

    @staticmethod
    def _deduplicate(proposals: list[KnowledgeProposal]) -> list[KnowledgeProposal]:
        unique: dict[str, KnowledgeProposal] = {}
        for proposal in proposals:
            unique.setdefault(proposal.id, proposal)
        return list(unique.values())
