"""Listening-layer orchestration and the handoff to Sprint 4 reasoning."""

from __future__ import annotations

import uuid

from app.schemas.listening import (
    EvidenceCluster,
    EvidenceObject,
    ListeningProposalResponse,
    NormalizedListeningSource,
    SourceSubmission,
)
from app.services.evidence_fusion import EvidenceFusionService
from app.services.knowledge_review_intelligence import KnowledgeReviewIntelligence
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
    """Synthesize fused evidence into concise, reviewable career memories."""

    def __init__(
        self,
        pipeline: KnowledgeReasoningPipeline,
        review_intelligence: KnowledgeReviewIntelligence | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._review_intelligence = review_intelligence or KnowledgeReviewIntelligence()

    async def generate(
        self,
        clusters: list[EvidenceCluster],
        existing_memory: list,
    ) -> ListeningProposalResponse:
        del existing_memory
        result = self._review_intelligence.synthesize(clusters)

        return ListeningProposalResponse(
            proposals=result.proposals,
            clusters_considered=len(clusters),
            evidence_considered=result.evidence_considered,
            provider=f"knowledge-review-intelligence:{self._pipeline.provider_name}",
            hidden_supporting_evidence_count=(result.hidden_supporting_evidence_count),
        )
