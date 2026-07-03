"""Extensible adapters that normalize untrusted source input."""

from __future__ import annotations

import hashlib
import re
import uuid
from typing import Protocol

from app.schemas.knowledge import SourceType
from app.schemas.listening import NormalizedListeningSource, SourceSubmission


class SourceAdapter(Protocol):
    """Convert one raw input format into the shared listening representation."""

    version: str

    def normalize(
        self, submission: SourceSubmission, user_id: uuid.UUID
    ) -> NormalizedListeningSource:
        """Normalize a source while retaining identity and provenance."""


class TextSourceAdapter:
    """Safe adapter for text supplied directly or extracted from a document."""

    version = "text-adapter-v1"
    _horizontal_space = re.compile(r"[\t\f\v ]+")

    def normalize(
        self, submission: SourceSubmission, user_id: uuid.UUID
    ) -> NormalizedListeningSource:
        text = submission.raw_text.replace("\r\n", "\n").replace("\r", "\n")
        normalized_lines = [
            self._horizontal_space.sub(" ", line).rstrip() for line in text.split("\n")
        ]
        normalized_text = "\n".join(normalized_lines).strip()
        content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
        source_id = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"careeros:{user_id}:{submission.source_type.value}:{content_hash}",
        )
        metadata = dict(submission.metadata)
        if submission.original_filename:
            metadata["original_filename"] = submission.original_filename
        if submission.media_type:
            metadata["media_type"] = submission.media_type
        if submission.source_url:
            metadata["source_url"] = submission.source_url

        return NormalizedListeningSource(
            id=source_id,
            user_id=user_id,
            source_type=submission.source_type,
            label=submission.label,
            raw_text=normalized_text,
            content_hash=content_hash,
            metadata=metadata,
            provenance={
                "label": submission.label,
                "source_type": submission.source_type.value,
                "content_hash": content_hash,
                "adapter_version": self.version,
                **metadata,
            },
            received_at=submission.received_at,
            adapter_version=self.version,
        )


class SourceAdapterRegistry:
    """Resolve adapters without coupling downstream services to source types."""

    def __init__(self, default: SourceAdapter | None = None) -> None:
        self._default = default or TextSourceAdapter()
        self._adapters: dict[SourceType, SourceAdapter] = {}

    def register(self, source_type: SourceType, adapter: SourceAdapter) -> None:
        self._adapters[source_type] = adapter

    def normalize(
        self, submission: SourceSubmission, user_id: uuid.UUID
    ) -> NormalizedListeningSource:
        adapter = self._adapters.get(submission.source_type, self._default)
        return adapter.normalize(submission, user_id)
