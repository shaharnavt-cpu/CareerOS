"""Listening-layer orchestration and the handoff to Sprint 4 reasoning."""

from __future__ import annotations

import uuid

from app.schemas.knowledge import EvidenceReference, ReasoningRequest
from app.schemas.listening import (
    EvidenceCategory,
    EvidenceCluster,
    EvidenceObject,
    ListeningProposalResponse,
    NormalizedListeningSource,
    SourceSubmission,
)
from app.services.evidence_fusion import EvidenceFusionService
from app.services.listeners import ListenerRegistry
from app.services.pipeline import KnowledgeReasoningPipeline
from app.services.source_adapters import SourceAdapterRegistry


class ListeningEngine:
    """Normalize, listen, and fuse without performing semantic reasoning."""

    def __init__(
        self,
        adapters: SourceAdapterRegistry | None = None,
        listeners: ListenerRegistry | None = None,
        fusion: EvidenceFusionService | None = None,
    ) -> None:
        self._adapters = adapters or SourceAdapterRegistry()
        self._listeners = listeners or ListenerRegistry()
        self._fusion = fusion or EvidenceFusionService()

    def listen(
        self, submission: SourceSubmission, user_id: uuid.UUID
    ) -> tuple[NormalizedListeningSource, list[EvidenceObject], list[EvidenceCluster]]:
        source = self._adapters.normalize(submission, user_id)
        evidence = self._listeners.listen(source)
        clusters = self._fusion.fuse(evidence)
        return source, evidence, clusters

    def fuse(self, evidence: list[EvidenceObject]) -> list[EvidenceCluster]:
        return self._fusion.fuse(evidence)


class ListeningReasoningBridge:
    """Feed fused evidence into, but never around, the Sprint 4 pipeline."""

    _headings = {
        EvidenceCategory.EDUCATION: "Education",
        EvidenceCategory.PROGRAM: "Programs",
        EvidenceCategory.EXPERIENCE: "Experience",
        EvidenceCategory.PROJECT: "Projects",
        EvidenceCategory.SKILL: "Skills",
        EvidenceCategory.ACHIEVEMENT: "Achievements",
    }

    def __init__(self, pipeline: KnowledgeReasoningPipeline) -> None:
        self._pipeline = pipeline

    async def generate(
        self,
        clusters: list[EvidenceCluster],
        existing_memory: list,
    ) -> ListeningProposalResponse:
        proposals = []
        provider = self._pipeline.provider_name
        eligible = [
            cluster for cluster in clusters if cluster.category in self._headings
        ]

        for cluster in eligible:
            heading = self._headings[cluster.category]
            raw_source = "\n".join(
                [heading, *(item.raw_excerpt for item in cluster.evidence)]
            )
            conflicts = [
                f"{claim.reason} {' versus '.join(claim.excerpts)}"
                for claim in cluster.conflicting_claims
            ]
            result = await self._pipeline.run(
                ReasoningRequest(
                    raw_source=raw_source,
                    source_type=cluster.evidence[0].source_type,
                    source_name=f"Evidence cluster: {cluster.label}",
                    existing_memory=existing_memory,
                    source_conflicts=conflicts,
                )
            )
            references = [
                EvidenceReference(
                    evidence_id=item.id,
                    source_id=str(item.source_id),
                    source_type=item.source_type,
                    title=str(item.provenance.get("label", "Career source")),
                    excerpt=item.raw_excerpt,
                    location=self._location(item),
                    category=item.category.value,
                    confidence=item.confidence,
                    corroborated=cluster.corroborated,
                )
                for item in cluster.evidence
            ]
            proposals.extend(
                proposal.model_copy(update={"evidence": references})
                for proposal in result.proposals
            )

        return ListeningProposalResponse(
            proposals=proposals,
            clusters_considered=len(eligible),
            evidence_considered=sum(len(cluster.evidence) for cluster in eligible),
            provider=provider,
        )

    @staticmethod
    def _location(item: EvidenceObject) -> str:
        parts = []
        if item.location.get("section"):
            parts.append(str(item.location["section"]))
        if item.location.get("line"):
            parts.append(f"line {item.location['line']}")
        return ", ".join(parts) or "source"
