"""Deterministic confidence aggregation and clarification reasons."""

from app.schemas.knowledge import (
    ClarificationReason,
    ExtractedCandidate,
    SemanticAssessment,
)


class ConfidenceAggregator:
    """Combine extraction, semantic, and evidence signals predictably."""

    review_threshold = 0.7

    def aggregate(
        self,
        candidate: ExtractedCandidate,
        assessment: SemanticAssessment,
        *,
        has_evidence: bool,
    ) -> float:
        evidence_score = 1.0 if has_evidence else 0.0
        score = (
            candidate.extraction_confidence * 0.45
            + assessment.semantic_confidence * 0.4
            + evidence_score * 0.15
        )
        score -= min(len(assessment.missing_fields) * 0.06, 0.24)
        score -= min(len(assessment.conflicting_evidence) * 0.12, 0.36)
        return round(max(0.0, min(1.0, score)), 3)

    def clarification_reason(
        self,
        confidence: float,
        assessment: SemanticAssessment,
        *,
        has_evidence: bool,
    ) -> ClarificationReason | None:
        if not has_evidence:
            return ClarificationReason.MISSING_EVIDENCE
        if assessment.conflicting_evidence:
            return ClarificationReason.CONFLICTING_EVIDENCE
        if confidence < self.review_threshold:
            return ClarificationReason.LOW_CONFIDENCE
        return None
