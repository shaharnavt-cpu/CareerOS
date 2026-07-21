r"""One-shot, fictional-data OpenAI application-writer smoke test.

Run from ``backend`` as::

    .\.venv\Scripts\python.exe -m scripts.live_application_writer_smoke

The script never prints the request payload, credential, or generated draft.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import TextIO

from app.core.config import Settings
from app.fixtures.application_writing_demo import (
    build_maya_chen_demo_writing_input,
)
from app.services.application_writing_provider import (
    ApplicationWriterDataPolicy,
    ApplicationWritingErrorCode,
    ApplicationWritingInput,
    ApplicationWritingOutput,
    ApplicationWritingProvider,
    ApplicationWritingProviderError,
    OpenAIApplicationWritingProvider,
    validate_application_writing_data_policy,
    validate_application_writing_output_contract,
)

ProviderFactory = Callable[[Settings], ApplicationWritingProvider]


def _openai_provider(settings: Settings) -> ApplicationWritingProvider:
    return OpenAIApplicationWritingProvider(settings)


def validate_demo_smoke_output(
    writing_input: ApplicationWritingInput,
    output: ApplicationWritingOutput,
) -> None:
    """Apply compact deterministic checks to the fictional smoke result."""

    memory_ids = {memory.memory_id for memory in writing_input.selected_memories}
    evidence_ids = {
        reference
        for memory in writing_input.selected_memories
        for reference in memory.evidence_reference_ids
    }
    evidence_ids.update(
        reference
        for enrichment in writing_input.approved_enrichment
        for reference in enrichment.evidence_reference_ids
    )

    required_question_ids = [
        question.question_id
        for question in writing_input.application_questions
        if question.required
    ]
    answer_question_ids = [
        snippet.question_id for snippet in output.application_snippets
    ]
    if answer_question_ids != required_question_ids:
        raise ValueError(
            "output did not answer the explicit required demo questions in order"
        )

    used = output.evidence_references_used
    if not used or any(
        item.memory_id not in memory_ids
        or item.evidence_reference_id not in evidence_ids
        for item in used
    ):
        raise ValueError("output referenced evidence outside the demo fixture")

    surfaced_references = [
        *output.cover_letter.evidence_reference_ids,
        *(
            reference
            for group in output.resume_bullet_groups
            for bullet in group.bullets
            for reference in bullet.evidence_reference_ids
        ),
        *(
            reference
            for snippet in output.application_snippets
            for reference in snippet.evidence_reference_ids
        ),
    ]
    if any(reference not in evidence_ids for reference in surfaced_references):
        raise ValueError("draft surface referenced evidence outside the demo fixture")
    if output.unsupported_claim_candidates:
        raise ValueError("provider reported unsupported generated claims")

    generated_surfaces = " ".join(
        [
            output.positioning_summary,
            output.cover_letter.full_text,
            *(
                bullet.text
                for group in output.resume_bullet_groups
                for bullet in group.bullets
            ),
            *(snippet.answer for snippet in output.application_snippets),
        ]
    ).casefold()
    if any(
        claim.casefold() in generated_surfaces
        for claim in writing_input.prohibited_claims
    ):
        raise ValueError("draft surfaced a prohibited claim")


def run_smoke(
    *,
    settings: Settings | None = None,
    provider_factory: ProviderFactory = _openai_provider,
    stdout: TextIO | None = None,
) -> int:
    """Run one gated provider generation and return a process exit code."""

    output_stream = stdout or sys.stdout
    resolved_settings = settings or Settings()
    if not resolved_settings.run_live_openai_tests:
        print(
            "FAIL: live test disabled; set RUN_LIVE_OPENAI_TESTS=true.",
            file=output_stream,
        )
        return 2
    if resolved_settings.application_writer_data_policy != "demo-shared":
        print(
            "FAIL: APPLICATION_WRITER_DATA_POLICY must be demo-shared.",
            file=output_stream,
        )
        return 2
    if resolved_settings.application_writer_provider != "openai":
        print(
            "FAIL: APPLICATION_WRITER_PROVIDER must be openai.",
            file=output_stream,
        )
        return 2
    if resolved_settings.openai_application_writer_model != "gpt-5.6-terra":
        print(
            "FAIL: OPENAI_APPLICATION_WRITER_MODEL must be gpt-5.6-terra.",
            file=output_stream,
        )
        return 2
    if (
        resolved_settings.openai_application_enable_review_pass
        and resolved_settings.openai_application_review_model != "gpt-5.6-sol"
    ):
        print(
            "FAIL: an enabled review pass requires gpt-5.6-sol.",
            file=output_stream,
        )
        return 2

    writing_input = build_maya_chen_demo_writing_input()
    try:
        validate_application_writing_data_policy(
            writing_input, ApplicationWriterDataPolicy.DEMO_SHARED
        )
        provider = provider_factory(resolved_settings)
        result = ApplicationWritingOutput.model_validate(
            provider.generate_application_draft(writing_input)
        )
        validate_application_writing_output_contract(writing_input, result)
        validate_demo_smoke_output(writing_input, result)
    except ApplicationWritingProviderError as exc:
        diagnostic = exc.validation_diagnostic
        if diagnostic is not None:
            print(
                "validation_rule_code: "
                f"{diagnostic.validation_rule_code.value}",
                file=output_stream,
            )
            print(
                f"output_section: {diagnostic.output_section}",
                file=output_stream,
            )
            print(f"field_path: {diagnostic.field_path}", file=output_stream)
            print(
                "normalized_disputed_phrase: "
                f"{diagnostic.normalized_disputed_phrase}",
                file=output_stream,
            )
            print(
                "referenced_evidence_ids: "
                f"{json.dumps(diagnostic.referenced_evidence_ids)}",
                file=output_stream,
            )
            print(
                "expected_evidence_category: "
                f"{diagnostic.expected_evidence_category}",
                file=output_stream,
            )
            print(
                "surface_classification: "
                f"{diagnostic.surface_classification}",
                file=output_stream,
            )
        else:
            print(f"FAIL: {exc.code.value}: {exc.safe_message}", file=output_stream)
        return 1
    except Exception:
        print(
            f"FAIL: {ApplicationWritingErrorCode.PROVIDER.value}: "
            "application-writer smoke validation failed.",
            file=output_stream,
        )
        return 1

    metadata = result.provider_metadata
    print("PASS", file=output_stream)
    print(f"provider: {metadata.provider}", file=output_stream)
    print(f"model: {metadata.model}", file=output_stream)
    print(f"latency_ms: {metadata.latency_ms}", file=output_stream)
    if metadata.input_tokens is not None:
        print(f"input_tokens: {metadata.input_tokens}", file=output_stream)
    if metadata.cached_input_tokens is not None:
        print(
            f"cached_input_tokens: {metadata.cached_input_tokens}",
            file=output_stream,
        )
    if metadata.output_tokens is not None:
        print(f"output_tokens: {metadata.output_tokens}", file=output_stream)
    print(f"review_pass_ran: {metadata.review_pass_ran}", file=output_stream)
    print("validation: PASS", file=output_stream)
    return 0


def main() -> int:
    return run_smoke()


if __name__ == "__main__":
    raise SystemExit(main())
