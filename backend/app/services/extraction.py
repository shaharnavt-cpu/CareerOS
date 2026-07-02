"""Deterministic entity identification over normalized source lines."""

import hashlib
import re

from app.schemas.knowledge import EntityType, ExtractedCandidate, NormalizedSource


class EntityExtractor:
    """Identify candidate boundaries without making semantic claims."""

    _section_types = {
        "education": EntityType.EDUCATION,
        "academic background": EntityType.EDUCATION,
        "experience": EntityType.EXPERIENCE,
        "work experience": EntityType.EXPERIENCE,
        "professional experience": EntityType.EXPERIENCE,
        "projects": EntityType.PROJECT,
        "selected projects": EntityType.PROJECT,
        "skills": EntityType.SKILL,
        "technical skills": EntityType.SKILL,
        "achievements": EntityType.ACHIEVEMENT,
        "awards": EntityType.ACHIEVEMENT,
        "certifications": EntityType.ACHIEVEMENT,
        "publications": EntityType.ACHIEVEMENT,
        "programs": EntityType.PROGRAM,
    }
    _date_only = re.compile(
        r"^(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\w*\s+)?"
        r"\d{4}\s*(?:-|–|—|to)\s*(?:present|current|"
        r"(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\w*\s+)?"
        r"\d{4})$",
        re.IGNORECASE,
    )

    def extract(self, source: NormalizedSource) -> list[ExtractedCandidate]:
        candidates: list[ExtractedCandidate] = []
        current_section: EntityType | None = None

        for line in source.lines:
            section = self._section_types.get(line.text.rstrip(":").casefold())
            if section:
                current_section = section
                continue
            if self._date_only.match(line.text):
                continue

            hinted_type = current_section or self._infer_hint(line.text)
            values = (
                self._split_skill_values(line.text)
                if hinted_type is EntityType.SKILL
                else [line.text]
            )

            for value in values:
                if len(value) < 2:
                    continue
                digest = hashlib.sha256(
                    f"{source.id}:{line.number}:{value.casefold()}".encode()
                ).hexdigest()[:20]
                candidates.append(
                    ExtractedCandidate(
                        id=f"candidate-{digest}",
                        hinted_type=hinted_type,
                        raw_value=value,
                        location=f"line {line.number}",
                        evidence_excerpt=line.text,
                        extraction_confidence=0.82 if hinted_type else 0.48,
                    )
                )

        return candidates

    def _infer_hint(self, value: str) -> EntityType | None:
        folded = value.casefold()
        if any(
            term in folded for term in ("university", "college", "b.s.", "m.s.", "ph.d")
        ):
            return EntityType.EDUCATION
        if any(
            term in folded
            for term in ("award", "scholarship", "certified", "publication")
        ):
            return EntityType.ACHIEVEMENT
        if "project" in folded or "capstone" in folded:
            return EntityType.PROJECT
        if " at " in folded:
            return EntityType.EXPERIENCE
        if "program" in folded or "cohort" in folded:
            return EntityType.PROGRAM
        return None

    @staticmethod
    def _split_skill_values(value: str) -> list[str]:
        value = re.sub(r"^[^:]{1,32}:\s*", "", value)
        parts = re.split(r"[,|;/]", value)
        return [part.strip() for part in parts if part.strip()]
