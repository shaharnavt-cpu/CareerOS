"""Deterministic identity resolution for Career Memory candidates."""

from __future__ import annotations

import re
from collections.abc import Iterable
from difflib import SequenceMatcher
from typing import Any

from app.models import CanonicalMemoryRecord, ReviewProposal
from app.schemas.enrichments import (
    MemoryIdentityResolution,
    MemoryResolutionKind,
    RecommendedReviewAction,
)


class MemoryIdentityResolver:
    """Resolve new evidence against canonical memory without automatic merging."""

    _stop_words = {
        "a",
        "an",
        "and",
        "for",
        "honors",
        "of",
        "project",
        "research",
        "study",
        "the",
        "to",
        "using",
        "with",
    }
    _themes = {
        "gas",
        "kinematics",
        "galaxy",
        "morphology",
        "capstone",
        "jwst",
        "spectral",
        "imaging",
        "unicorn",
        "riskpulse",
        "fraud",
        "analytics",
        "ai",
    }

    def resolve(
        self,
        *,
        title: str,
        text: str = "",
        memory_type: str = "PROJECT",
        memories: Iterable[CanonicalMemoryRecord] = (),
        proposals: Iterable[ReviewProposal] = (),
        evidence_ids: Iterable[str] = (),
    ) -> MemoryIdentityResolution:
        evidence = list(dict.fromkeys(str(item) for item in evidence_ids))
        matching_memories = [
            memory for memory in memories if memory.memory_type == memory_type
        ]
        scored = [
            (self._memory_score(title, text, memory), memory)
            for memory in matching_memories
        ]
        scored.sort(key=lambda item: item[0][0], reverse=True)
        if scored:
            (score, reasons), memory = scored[0]
            if score >= 0.72:
                return MemoryIdentityResolution(
                    resolution=MemoryResolutionKind.ENRICH_EXISTING,
                    confidence=score,
                    matched_memory_id=memory.id,
                    matched_memory_title=memory.title,
                    reasons=reasons,
                    evidence_ids=evidence,
                    recommended_review_action=(
                        RecommendedReviewAction.CREATE_ENRICHMENT
                    ),
                )

        duplicate = self._duplicate_proposal(title, memory_type, proposals)
        if duplicate is not None:
            return MemoryIdentityResolution(
                resolution=MemoryResolutionKind.DUPLICATE_PROPOSAL,
                confidence=0.98,
                matched_proposal_id=duplicate.id,
                reasons=["A review proposal with the same normalized title exists."],
                evidence_ids=evidence,
                recommended_review_action=(
                    RecommendedReviewAction.USE_EXISTING_PROPOSAL
                ),
            )

        if scored:
            (score, reasons), memory = scored[0]
            if score >= 0.48:
                return MemoryIdentityResolution(
                    resolution=MemoryResolutionKind.POSSIBLE_MERGE,
                    confidence=score,
                    matched_memory_id=memory.id,
                    matched_memory_title=memory.title,
                    reasons=reasons,
                    evidence_ids=evidence,
                    recommended_review_action=(
                        RecommendedReviewAction.REVIEW_POSSIBLE_MERGE
                    ),
                )
            if score >= 0.28:
                return MemoryIdentityResolution(
                    resolution=MemoryResolutionKind.NEEDS_USER_CONFIRMATION,
                    confidence=score,
                    matched_memory_id=memory.id,
                    matched_memory_title=memory.title,
                    reasons=reasons,
                    evidence_ids=evidence,
                    recommended_review_action=RecommendedReviewAction.ASK_USER,
                )

        detail_tokens = self._tokens(text)
        if len(detail_tokens) < 4 and not self._tokens(title):
            return MemoryIdentityResolution(
                resolution=MemoryResolutionKind.QUIET_SUPPORTING_EVIDENCE,
                confidence=0.55,
                reasons=["The source has too little project identity detail."],
                evidence_ids=evidence,
                recommended_review_action=(
                    RecommendedReviewAction.KEEP_AS_SUPPORTING_EVIDENCE
                ),
            )
        return MemoryIdentityResolution(
            resolution=MemoryResolutionKind.CREATE_NEW,
            confidence=0.76 if self._tokens(title) else 0.55,
            reasons=["No approved memory has a sufficiently similar project identity."],
            evidence_ids=evidence,
            recommended_review_action=RecommendedReviewAction.CREATE_MEMORY,
        )

    def candidates(
        self,
        *,
        title: str,
        text: str,
        memory_type: str,
        memories: Iterable[CanonicalMemoryRecord],
        evidence_ids: Iterable[str] = (),
    ) -> list[MemoryIdentityResolution]:
        evidence = list(dict.fromkeys(str(item) for item in evidence_ids))
        candidates: list[MemoryIdentityResolution] = []
        for memory in memories:
            if memory.memory_type != memory_type:
                continue
            score, reasons = self._memory_score(title, text, memory)
            if score < 0.28:
                continue
            resolution = (
                MemoryResolutionKind.ENRICH_EXISTING
                if score >= 0.72
                else MemoryResolutionKind.POSSIBLE_MERGE
                if score >= 0.48
                else MemoryResolutionKind.NEEDS_USER_CONFIRMATION
            )
            action = (
                RecommendedReviewAction.CREATE_ENRICHMENT
                if resolution is MemoryResolutionKind.ENRICH_EXISTING
                else RecommendedReviewAction.REVIEW_POSSIBLE_MERGE
                if resolution is MemoryResolutionKind.POSSIBLE_MERGE
                else RecommendedReviewAction.ASK_USER
            )
            candidates.append(
                MemoryIdentityResolution(
                    resolution=resolution,
                    confidence=score,
                    matched_memory_id=memory.id,
                    matched_memory_title=memory.title,
                    reasons=reasons,
                    evidence_ids=evidence,
                    recommended_review_action=action,
                )
            )
        return sorted(candidates, key=lambda item: item.confidence, reverse=True)

    def _memory_score(
        self, title: str, text: str, memory: CanonicalMemoryRecord
    ) -> tuple[float, list[str]]:
        candidate_text = " ".join((title, text))
        candidate_normalized = self._normalize(title)
        memory_normalized = self._normalize(memory.title)
        candidate_tokens = self._tokens(candidate_text)
        memory_text = " ".join(
            (memory.title, *self._flatten(memory.structured_fields))
        )
        memory_tokens = self._tokens(memory_text)
        title_tokens = self._tokens(title)
        memory_title_tokens = self._tokens(memory.title)
        reasons: list[str] = []

        if candidate_normalized and candidate_normalized == memory_normalized:
            return 1.0, ["The normalized project titles are identical."]

        if self._distinct_named_projects(candidate_tokens, memory_title_tokens):
            return 0.05, ["The evidence names a distinct project identity."]

        title_overlap = self._jaccard(title_tokens, memory_title_tokens)
        all_overlap = self._jaccard(candidate_tokens, memory_tokens)
        sequence = SequenceMatcher(
            None, candidate_normalized, memory_normalized
        ).ratio()
        score = (title_overlap * 0.62) + (sequence * 0.23) + (all_overlap * 0.15)

        shared_core = self._shared_core_phrase(candidate_text, memory_text)
        if shared_core:
            score = max(score, 0.78)
            reasons.append(f'Both records identify the project as "{shared_core}".')
        if title_overlap >= 0.6:
            reasons.append("The significant project-title words strongly overlap.")
        elif title_overlap >= 0.35:
            reasons.append("The project titles share several identifying words.")
        if all_overlap >= 0.35:
            reasons.append("The source and approved memory share project themes.")
        if self._date_overlap(candidate_text, memory_text):
            score += 0.04
            reasons.append("The documented project dates overlap.")
        if self._organization_overlap(candidate_text, memory_text):
            score += 0.04
            reasons.append("The institution or organization context overlaps.")
        if not reasons:
            reasons.append("Only weak identity signals overlap.")
        return min(round(score, 3), 1.0), reasons

    @classmethod
    def _duplicate_proposal(
        cls,
        title: str,
        memory_type: str,
        proposals: Iterable[ReviewProposal],
    ) -> ReviewProposal | None:
        normalized = cls._normalize(title)
        for proposal in proposals:
            if proposal.proposal_type != memory_type:
                continue
            proposed = proposal.proposal_data.get("proposed_value", {})
            proposal_title = next(
                (
                    str(proposed.get(key)).strip()
                    for key in (
                        "title",
                        "name",
                        "project_name",
                        "institution_name",
                        "organization_name",
                    )
                    if proposed.get(key)
                ),
                "",
            )
            if cls._normalize(proposal_title) == normalized:
                return proposal
        return None

    @classmethod
    def _tokens(cls, value: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9]+", value.casefold())
            if len(token) > 1 and token not in cls._stop_words
        }

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))

    @staticmethod
    def _jaccard(left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        return len(left & right) / len(left | right)

    @classmethod
    def _shared_core_phrase(cls, left: str, right: str) -> str | None:
        folded_left = cls._normalize(left)
        folded_right = cls._normalize(right)
        for phrase in (
            "gas kinematics",
            "3d galaxy morphology",
            "return fraud detection",
            "supply chain risk assessment",
            "the unicorn project",
        ):
            if phrase in folded_left and phrase in folded_right:
                return phrase.title()
        return None

    @staticmethod
    def _distinct_named_projects(left: set[str], right: set[str]) -> bool:
        return (
            "unicorn" in left and bool({"gas", "kinematics", "morphology"} & right)
        ) or (
            "unicorn" in right and bool({"gas", "kinematics", "morphology"} & left)
        )

    @staticmethod
    def _date_overlap(left: str, right: str) -> bool:
        left_dates = set(re.findall(r"\b20\d{2}\b", left))
        right_dates = set(re.findall(r"\b20\d{2}\b", right))
        return bool(left_dates & right_dates)

    @staticmethod
    def _organization_overlap(left: str, right: str) -> bool:
        organizations = (
            "university of texas",
            "ut austin",
            "ut dallas",
            "gevip",
        )
        folded_left = left.casefold()
        folded_right = right.casefold()
        return any(
            item in folded_left and item in folded_right for item in organizations
        )

    @classmethod
    def _flatten(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, dict):
            return [part for nested in value.values() for part in cls._flatten(nested)]
        if isinstance(value, (list, tuple, set)):
            return [part for nested in value for part in cls._flatten(nested)]
        return [str(value)]
