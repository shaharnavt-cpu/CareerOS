"""Deterministic grouping that retains duplicates, support, and conflicts."""

from __future__ import annotations

import re
import uuid
from difflib import SequenceMatcher

from app.schemas.listening import (
    ConflictingClaim,
    EvidenceCluster,
    EvidenceObject,
)


class EvidenceFusionService:
    """Group related observations without selecting a winning claim."""

    _word = re.compile(r"[a-z0-9+#.]+")
    _year = re.compile(r"\b(?:19|20)\d{2}\b")
    _stop_words = {
        "a",
        "an",
        "and",
        "at",
        "for",
        "from",
        "in",
        "my",
        "of",
        "on",
        "the",
        "to",
        "was",
        "with",
    }

    def fuse(self, evidence: list[EvidenceObject]) -> list[EvidenceCluster]:
        clusters: list[EvidenceCluster] = []
        for item in evidence:
            cluster = next(
                (
                    candidate
                    for candidate in clusters
                    if candidate.category is item.category
                    and self._related(candidate.evidence, item)
                ),
                None,
            )
            if cluster is None:
                key = self._key(item)
                cluster = EvidenceCluster(
                    id=uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        f"careeros:cluster:{item.category.value}:{item.source_id}:{key}",
                    ),
                    category=item.category,
                    label=item.raw_excerpt,
                    normalized_key=key,
                    evidence=[item],
                )
                clusters.append(cluster)
            else:
                cluster.evidence.append(item)

        for cluster in clusters:
            self._finalize(cluster)
        return clusters

    def _related(self, existing: list[EvidenceObject], item: EvidenceObject) -> bool:
        item_key = self._key(item)
        item_tokens = set(item_key.split())
        item_claim = item.provenance.get("claim_key")
        for other in existing:
            other_key = self._key(other)
            if item_key == other_key:
                return True
            if item_claim and item_claim == other.provenance.get("claim_key"):
                return True
            if self._anchors(item.raw_excerpt) & self._anchors(other.raw_excerpt):
                return True
            other_tokens = set(other_key.split())
            union = item_tokens | other_tokens
            overlap = len(item_tokens & other_tokens) / len(union) if union else 0
            if overlap >= 0.55:
                return True
            if SequenceMatcher(None, item_key, other_key).ratio() >= 0.82:
                return True
        return False

    def _finalize(self, cluster: EvidenceCluster) -> None:
        cluster.contributing_source_ids = list(
            dict.fromkeys(item.source_id for item in cluster.evidence)
        )
        cluster.corroborated = len(cluster.contributing_source_ids) > 1
        cluster.conflicting_claims = self._conflicts(cluster.evidence)
        cluster.normalized_key = self._stable_cluster_key(cluster.evidence)
        source_key = ":".join(
            sorted(str(value) for value in cluster.contributing_source_ids)
        )
        cluster.id = uuid.uuid5(
            uuid.NAMESPACE_URL,
            "careeros:cluster:"
            f"{cluster.category.value}:{source_key}:{cluster.normalized_key}",
        )

    def _conflicts(self, evidence: list[EvidenceObject]) -> list[ConflictingClaim]:
        conflicts: list[ConflictingClaim] = []
        for index, left in enumerate(evidence):
            for right in evidence[index + 1 :]:
                reason = self._conflict_reason(left, right)
                if reason:
                    conflicts.append(
                        ConflictingClaim(
                            evidence_ids=[left.id, right.id],
                            excerpts=[left.raw_excerpt, right.raw_excerpt],
                            reason=reason,
                        )
                    )
        return conflicts

    def _conflict_reason(
        self, left: EvidenceObject, right: EvidenceObject
    ) -> str | None:
        left_years = set(self._year.findall(left.raw_excerpt))
        right_years = set(self._year.findall(right.raw_excerpt))
        if left_years and right_years and left_years != right_years:
            return "Comparable evidence contains different dates."
        left_claim = left.provenance.get("claim_key")
        right_claim = right.provenance.get("claim_key")
        if (
            left_claim
            and left_claim == right_claim
            and self._normalized(left) != self._normalized(right)
        ):
            return "Sources provide different values for the same claim."
        left_negated = bool(
            re.search(r"\b(?:not|never|didn't|did not)\b", left.raw_excerpt, re.I)
        )
        right_negated = bool(
            re.search(r"\b(?:not|never|didn't|did not)\b", right.raw_excerpt, re.I)
        )
        if left_negated != right_negated:
            return "Sources contain opposing statements about the same subject."
        return None

    def _key(self, evidence: EvidenceObject) -> str:
        value = self._year.sub(" ", self._normalized(evidence))
        tokens = [
            token
            for token in self._word.findall(value)
            if token not in self._stop_words and len(token) > 1
        ]
        anchors = self._anchors(evidence.raw_excerpt)
        if anchors:
            return sorted(anchors)[0]
        return " ".join(tokens) or self._normalized(evidence)

    def _stable_cluster_key(self, evidence: list[EvidenceObject]) -> str:
        keys = sorted({self._key(item) for item in evidence})
        return min(keys, key=lambda value: (len(value), value))

    @staticmethod
    def _normalized(evidence: EvidenceObject) -> str:
        return (
            evidence.normalized_excerpt
            or re.sub(r"\s+", " ", evidence.raw_excerpt.casefold()).strip()
        )

    @staticmethod
    def _anchors(value: str) -> set[str]:
        explicit = {
            token.casefold() for token in re.findall(r"\b[A-Z][A-Z0-9]{1,9}\b", value)
        }
        words = re.findall(r"\b[A-Za-z]+\b", value)
        if len(words) >= 3:
            acronym = "".join(word[0] for word in words if len(word) > 2).casefold()
            if 2 <= len(acronym) <= 10:
                explicit.add(acronym)
        return explicit
