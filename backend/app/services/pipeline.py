"""End-to-end hybrid Knowledge Reasoning Engine orchestration."""

from app.schemas.knowledge import ProcessingSummary, ReasoningRequest, ReasoningResponse
from app.services.extraction import EntityExtractor
from app.services.llm import SemanticReasoningProvider
from app.services.normalization import SourceNormalizer
from app.services.proposals import ProposalBuilder


class KnowledgeReasoningPipeline:
    """Preserve the deterministic/LLM/deterministic processing boundary."""

    def __init__(
        self,
        provider: SemanticReasoningProvider,
        normalizer: SourceNormalizer | None = None,
        extractor: EntityExtractor | None = None,
        proposal_builder: ProposalBuilder | None = None,
    ) -> None:
        self._provider = provider
        self._normalizer = normalizer or SourceNormalizer()
        self._extractor = extractor or EntityExtractor()
        self._proposal_builder = proposal_builder or ProposalBuilder()

    @property
    def provider_name(self) -> str:
        """Expose safe provider metadata to upstream orchestrators."""

        return self._provider.name

    async def run(self, request: ReasoningRequest) -> ReasoningResponse:
        source = self._normalizer.normalize(request)
        candidates = self._extractor.extract(source)
        assessments = await self._provider.reason(source, candidates)
        if request.source_conflicts:
            assessments = [
                assessment.model_copy(
                    update={
                        "conflicting_evidence": list(
                            dict.fromkeys(
                                [
                                    *assessment.conflicting_evidence,
                                    *request.source_conflicts,
                                ]
                            )
                        )
                    }
                )
                for assessment in assessments
            ]
        proposals = self._proposal_builder.build(
            source, candidates, assessments, request.existing_memory
        )
        return ReasoningResponse(
            source_id=source.id,
            proposals=proposals,
            summary=ProcessingSummary(
                normalized_lines=len(source.lines),
                extracted_candidates=len(candidates),
                proposals=len(proposals),
                provider=self._provider.name,
            ),
        )
