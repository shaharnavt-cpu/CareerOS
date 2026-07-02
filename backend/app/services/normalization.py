"""Deterministic normalization for raw career sources."""

import hashlib
import re

from app.schemas.knowledge import NormalizedLine, NormalizedSource, ReasoningRequest


class SourceNormalizer:
    """Convert supported raw sources into one stable, addressable shape."""

    _horizontal_whitespace = re.compile(r"[\t\f\v ]+")

    def normalize(self, request: ReasoningRequest) -> NormalizedSource:
        text = request.raw_source.replace("\r\n", "\n").replace("\r", "\n")
        lines: list[NormalizedLine] = []

        for original_number, raw_line in enumerate(text.split("\n"), start=1):
            normalized = self._horizontal_whitespace.sub(" ", raw_line).strip()
            normalized = normalized.lstrip("•*-–— ").strip()
            if normalized:
                lines.append(NormalizedLine(number=original_number, text=normalized))

        canonical_text = "\n".join(line.text for line in lines)
        content_hash = hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()
        source_id = f"{request.source_type.value.lower()}-{content_hash[:20]}"

        return NormalizedSource(
            id=source_id,
            source_type=request.source_type,
            name=request.source_name,
            content_hash=content_hash,
            lines=lines,
        )
