"""Deterministic source listeners that extract observations, not conclusions."""

from __future__ import annotations

import hashlib
import re
import uuid
from typing import Protocol

from app.schemas.knowledge import SourceType
from app.schemas.listening import (
    EvidenceCategory,
    EvidenceObject,
    NormalizedListeningSource,
)


class SourceListener(Protocol):
    """Extract standardized evidence from a normalized source."""

    version: str

    def listen(self, source: NormalizedListeningSource) -> list[EvidenceObject]:
        """Return source observations without canonical classification."""


class LineListener:
    """Shared line-addressable extraction with source-specific section hints."""

    version = "line-listener-v1"
    section_categories: dict[str, EvidenceCategory] = {}
    default_category = EvidenceCategory.UNKNOWN
    _date = re.compile(
        r"\b(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)"
        r"[a-z]*\s+)?(?:19|20)\d{2}\b",
        re.IGNORECASE,
    )
    _url = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)
    _email = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
    _role_at_organization = re.compile(
        r"^(?P<role>.+?)\s+at\s+(?P<organization>.+?)(?:\s*[|,;]\s*|$)",
        re.IGNORECASE,
    )

    def listen(self, source: NormalizedListeningSource) -> list[EvidenceObject]:
        evidence: list[EvidenceObject] = []
        section: str | None = None
        section_category = self.default_category

        for line_number, original in enumerate(source.raw_text.split("\n"), start=1):
            excerpt = original.strip().lstrip("•*-–— ").strip()
            if not excerpt:
                continue
            heading = excerpt.rstrip(":").casefold()
            if heading in self.section_categories:
                section = excerpt.rstrip(":")
                section_category = self.section_categories[heading]
                continue

            category, confidence = self._categorize(excerpt, section_category)
            primary_excerpts = self._primary_excerpts(excerpt, category)
            for primary_index, primary_excerpt in enumerate(primary_excerpts):
                evidence.append(
                    self._make_evidence(
                        source,
                        primary_excerpt,
                        category,
                        confidence,
                        line_number,
                        section,
                        fragment=f"line-{primary_index}",
                        context=excerpt,
                    )
                )
            role_match = self._role_at_organization.match(excerpt)
            if role_match:
                evidence.extend(
                    [
                        self._make_evidence(
                            source,
                            role_match.group("role").strip(),
                            EvidenceCategory.ROLE,
                            0.86,
                            line_number,
                            section,
                            fragment="role",
                            context=excerpt,
                        ),
                        self._make_evidence(
                            source,
                            role_match.group("organization").strip(),
                            EvidenceCategory.ORGANIZATION,
                            0.86,
                            line_number,
                            section,
                            fragment="organization",
                            context=excerpt,
                        ),
                    ]
                )
            for match in self._date.finditer(excerpt):
                evidence.append(
                    self._make_evidence(
                        source,
                        match.group(0),
                        EvidenceCategory.DATE,
                        0.96,
                        line_number,
                        section,
                        fragment="date",
                        context=excerpt,
                    )
                )
            for match in self._url.finditer(excerpt):
                evidence.append(
                    self._make_evidence(
                        source,
                        match.group(0).rstrip(".,)"),
                        EvidenceCategory.LINK,
                        0.99,
                        line_number,
                        section,
                        fragment="link",
                        context=excerpt,
                    )
                )
            for match in self._email.finditer(excerpt):
                evidence.append(
                    self._make_evidence(
                        source,
                        match.group(0),
                        EvidenceCategory.CONTACT,
                        0.99,
                        line_number,
                        section,
                        fragment="email",
                        context=excerpt,
                    )
                )
        return evidence

    @staticmethod
    def _primary_excerpts(excerpt: str, category: EvidenceCategory) -> list[str]:
        if category is not EvidenceCategory.SKILL:
            return [excerpt]
        value = re.sub(r"^[^:]{1,32}:\s*", "", excerpt)
        fragments = [item.strip() for item in re.split(r"[,|;/]", value)]
        return [item for item in fragments if item] or [excerpt]

    def _categorize(
        self, excerpt: str, section_category: EvidenceCategory
    ) -> tuple[EvidenceCategory, float]:
        if section_category is not EvidenceCategory.UNKNOWN:
            return section_category, 0.9
        folded = excerpt.casefold()
        signals = (
            (EvidenceCategory.EDUCATION, ("university", "college", "degree", "gpa")),
            (EvidenceCategory.PROGRAM, (" program", "cohort", "fellowship")),
            (EvidenceCategory.PROJECT, ("project", "capstone", "repository")),
            (EvidenceCategory.ACHIEVEMENT, ("award", "scholarship", "presented")),
            (EvidenceCategory.EXPERIENCE, (" at ", "intern", "engineer", "manager")),
            (EvidenceCategory.SKILL, ("skills:", "technologies:", "proficient")),
        )
        for category, terms in signals:
            if any(term in folded for term in terms):
                return category, 0.72
        return self.default_category, 0.5

    def _make_evidence(
        self,
        source: NormalizedListeningSource,
        excerpt: str,
        category: EvidenceCategory,
        confidence: float,
        line_number: int,
        section: str | None,
        *,
        fragment: str,
        context: str | None = None,
    ) -> EvidenceObject:
        normalized = re.sub(r"\s+", " ", excerpt).strip().casefold()
        digest = hashlib.sha256(
            f"{source.id}:{line_number}:{fragment}:{normalized}".encode()
        ).hexdigest()
        evidence_id = uuid.uuid5(uuid.NAMESPACE_URL, f"careeros:evidence:{digest}")
        provenance = {
            **source.provenance,
            "listener_version": self.version,
        }
        if context and context != excerpt:
            provenance["context"] = context
        return EvidenceObject(
            id=evidence_id,
            source_id=source.id,
            source_type=source.source_type,
            raw_excerpt=excerpt,
            normalized_excerpt=normalized,
            category=category,
            confidence=confidence,
            location={
                "line": line_number,
                "section": section,
                "fragment": fragment,
            },
            provenance=provenance,
        )


class ResumeListener(LineListener):
    """Listen to resume/CV sections without deciding canonical entities."""

    version = "resume-listener-v1"
    section_categories = {
        "education": EvidenceCategory.EDUCATION,
        "academic background": EvidenceCategory.EDUCATION,
        "programs": EvidenceCategory.PROGRAM,
        "experience": EvidenceCategory.EXPERIENCE,
        "work experience": EvidenceCategory.EXPERIENCE,
        "professional experience": EvidenceCategory.EXPERIENCE,
        "projects": EvidenceCategory.PROJECT,
        "selected projects": EvidenceCategory.PROJECT,
        "skills": EvidenceCategory.SKILL,
        "technical skills": EvidenceCategory.SKILL,
        "achievements": EvidenceCategory.ACHIEVEMENT,
        "awards": EvidenceCategory.ACHIEVEMENT,
        "certifications": EvidenceCategory.ACHIEVEMENT,
    }


class TranscriptListener(LineListener):
    """Listen to transcript-like academic records."""

    version = "transcript-listener-v1"
    default_category = EvidenceCategory.EDUCATION
    section_categories = {
        "institution": EvidenceCategory.ORGANIZATION,
        "degree": EvidenceCategory.EDUCATION,
        "coursework": EvidenceCategory.EDUCATION,
        "honors": EvidenceCategory.ACHIEVEMENT,
        "awards": EvidenceCategory.ACHIEVEMENT,
    }


class ProfileListener(ResumeListener):
    """Listen to LinkedIn/profile-like text using profile section boundaries."""

    version = "profile-listener-v1"
    section_categories = {
        **ResumeListener.section_categories,
        "about": EvidenceCategory.UNKNOWN,
        "licenses & certifications": EvidenceCategory.ACHIEVEMENT,
        "volunteering": EvidenceCategory.EXPERIENCE,
    }


class NarrativeListener(LineListener):
    """Listen to conversations, manual entry, and generic prose."""

    version = "narrative-listener-v1"


class ListenerRegistry:
    """Select listeners by source type while keeping future adapters pluggable."""

    def __init__(self) -> None:
        resume = ResumeListener()
        narrative = NarrativeListener()
        self._listeners: dict[SourceType, SourceListener] = {
            SourceType.RESUME: resume,
            SourceType.TRANSCRIPT: TranscriptListener(),
            SourceType.LINKEDIN: ProfileListener(),
            SourceType.CONVERSATION: narrative,
            SourceType.MANUAL: narrative,
            SourceType.GENERIC_DOCUMENT: narrative,
            SourceType.PORTFOLIO: resume,
            SourceType.GITHUB: narrative,
            SourceType.CERTIFICATE: narrative,
        }
        self._default = narrative

    def register(self, source_type: SourceType, listener: SourceListener) -> None:
        self._listeners[source_type] = listener

    def listen(self, source: NormalizedListeningSource) -> list[EvidenceObject]:
        return self._listeners.get(source.source_type, self._default).listen(source)
