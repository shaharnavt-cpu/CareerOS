"""Explainable professional-document detection for Universal Listening."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from app.schemas.knowledge import SourceType


class DocumentType(StrEnum):
    """Likely semantic role of an uploaded professional artifact."""

    RESUME = "RESUME"
    TRANSCRIPT = "TRANSCRIPT"
    JOB_DESCRIPTION = "JOB_DESCRIPTION"
    CERTIFICATE = "CERTIFICATE"
    RESEARCH_PAPER = "RESEARCH_PAPER"
    PORTFOLIO = "PORTFOLIO"
    GENERIC_DOCUMENT = "GENERIC_DOCUMENT"


@dataclass(frozen=True)
class DocumentDetection:
    """Detected type with a user-explainable score and listener mapping."""

    document_type: DocumentType
    source_type: SourceType
    confidence: float
    reasons: tuple[str, ...]


class DocumentDetector:
    """Classify common career artifacts using deterministic content signals."""

    _signals: dict[DocumentType, tuple[str, ...]] = {
        DocumentType.RESUME: (
            "resume",
            "curriculum vitae",
            "work experience",
            "professional experience",
            "skills",
            "education",
        ),
        DocumentType.TRANSCRIPT: (
            "transcript",
            "credit hours",
            "cumulative gpa",
            "grade point average",
            "academic record",
            "course title",
        ),
        DocumentType.JOB_DESCRIPTION: (
            "job description",
            "responsibilities",
            "qualifications",
            "requirements",
            "salary range",
            "equal opportunity employer",
        ),
        DocumentType.CERTIFICATE: (
            "certificate",
            "certification",
            "has successfully completed",
            "credential id",
            "date of issue",
            "awarded to",
        ),
        DocumentType.RESEARCH_PAPER: (
            "abstract",
            "introduction",
            "methodology",
            "references",
            "doi",
            "et al.",
        ),
        DocumentType.PORTFOLIO: (
            "portfolio",
            "selected work",
            "case study",
            "view project",
            "project gallery",
            "my work",
        ),
    }
    _source_types = {
        DocumentType.RESUME: SourceType.RESUME,
        DocumentType.TRANSCRIPT: SourceType.TRANSCRIPT,
        DocumentType.CERTIFICATE: SourceType.CERTIFICATE,
        DocumentType.PORTFOLIO: SourceType.PORTFOLIO,
        DocumentType.JOB_DESCRIPTION: SourceType.GENERIC_DOCUMENT,
        DocumentType.RESEARCH_PAPER: SourceType.GENERIC_DOCUMENT,
        DocumentType.GENERIC_DOCUMENT: SourceType.GENERIC_DOCUMENT,
    }

    def detect(self, filename: str, text: str) -> DocumentDetection:
        content = re.sub(r"\s+", " ", text.casefold())[:50_000]
        stem = Path(filename).stem.casefold().replace("_", " ").replace("-", " ")
        scores: dict[DocumentType, int] = {}
        matched: dict[DocumentType, list[str]] = {}

        for document_type, signals in self._signals.items():
            score = 0
            reasons: list[str] = []
            for signal in signals:
                if signal in content:
                    score += 1
                    reasons.append(f"content includes “{signal}”")
                if signal in stem:
                    score += 3
                    reasons.append(f"filename includes “{signal}”")
            scores[document_type] = score
            matched[document_type] = reasons

        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        if best_score < 2:
            return DocumentDetection(
                document_type=DocumentType.GENERIC_DOCUMENT,
                source_type=SourceType.GENERIC_DOCUMENT,
                confidence=0.45,
                reasons=("No strong specialized-document pattern was found.",),
            )

        runner_up = sorted(scores.values(), reverse=True)[1]
        confidence = min(
            0.98, 0.55 + best_score * 0.06 + (best_score - runner_up) * 0.03
        )
        return DocumentDetection(
            document_type=best_type,
            source_type=self._source_types[best_type],
            confidence=round(confidence, 2),
            reasons=tuple(matched[best_type][:3]),
        )
