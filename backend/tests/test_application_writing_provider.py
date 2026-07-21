"""Focused provider, Structured Output, and data-policy tests."""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.services.application_writing_provider import (
    ApplicationAnswerRepairOutput,
    ApplicationQuestionInput,
    ApplicationSnippetOutput,
    ApplicationWriterDataPolicy,
    ApplicationWritingAuthenticationError,
    ApplicationWritingBillingError,
    ApplicationWritingConfigurationError,
    ApplicationWritingDataClassification,
    ApplicationWritingDataPolicyError,
    ApplicationWritingDataSource,
    ApplicationWritingInput,
    ApplicationWritingMalformedOutputError,
    ApplicationWritingOutput,
    ApplicationWritingRateLimitError,
    ApplicationWritingRefusalError,
    ApplicationWritingRemoteProviderError,
    ApplicationWritingRequirements,
    ApplicationWritingTimeoutError,
    ApplicationWritingValidationCode,
    ApprovedEvidenceAtom,
    CandidateClaimType,
    CandidateFacingClaim,
    ClaimCertainty,
    ClaimPlanOutput,
    CoverLetterSectionsOutput,
    EvidenceAtomSupportType,
    EvidenceReferenceUsed,
    JobUnderstandingOutput,
    LocalDeterministicApplicationWritingProvider,
    OpenAIApplicationWritingProvider,
    RequirementCoverageItem,
    RequirementCoverageLevel,
    ResumeBulletGroupOutput,
    ResumeBulletOutput,
    SelectedCompiledMemory,
    validate_application_writing_data_policy,
    validate_application_writing_output_contract,
)


def _application_questions() -> list[ApplicationQuestionInput]:
    return [
        ApplicationQuestionInput(
            question_id="motivation",
            question_text="Why are you interested in this role?",
            required=True,
        ),
        ApplicationQuestionInput(
            question_id="complex-data-project",
            question_text="Describe a project where you analyzed complex data.",
            required=True,
        ),
        ApplicationQuestionInput(
            question_id="quality-reliability",
            question_text="How did you ensure the quality of your work?",
            required=True,
        ),
    ]


def _writing_input(
    *,
    is_demo: bool = True,
    source: ApplicationWritingDataSource = (
        ApplicationWritingDataSource.SEEDED_FICTIONAL
    ),
    job_description: str = "Analyze scientific data and communicate findings.",
    application_questions: list[ApplicationQuestionInput] | None = None,
) -> ApplicationWritingInput:
    return ApplicationWritingInput(
        target_role="Data Science Intern",
        company="Fictional Analytics Lab",
        job_description=job_description,
        grouped_requirements=ApplicationWritingRequirements(
            must_have=["analytics", "communication"],
            concrete_tools_requiring_direct_proof=["Python"],
        ),
        central_responsibilities=["Analyze data", "Present findings"],
        application_questions=(
            _application_questions()
            if application_questions is None
            else application_questions
        ),
        selected_memories=[
            SelectedCompiledMemory(
                memory_id="memory-1",
                title="Scientific Data Research",
                memory_type="PROJECT",
                summary="Tested a research question with spectroscopy data.",
                approved_claims=["Built an analytical workflow in Python."],
                skills_and_tools=["Python"],
                evidence_reference_ids=["evidence-1"],
            )
        ],
        evidence_ledger=[
            ApprovedEvidenceAtom(
                evidence_atom_id="atom-target-role",
                canonical_memory_id=None,
                approved_claim_id="claim-target-role",
                evidence_reference_ids=[],
                support_type=EvidenceAtomSupportType.TARGET_CONTEXT,
                factual_statement=(
                    "The fictional target is a Data Science Intern role at "
                    "Fictional Analytics Lab."
                ),
                allowed_certainty=ClaimCertainty.ASPIRATIONAL,
                prohibited_expansions=[
                    "Target wording is relevance context, not candidate proof."
                ],
            ),
            ApprovedEvidenceAtom(
                evidence_atom_id="atom-memory-1-workflow",
                canonical_memory_id="memory-1",
                approved_claim_id="claim-memory-1-workflow",
                evidence_reference_ids=["evidence-1"],
                support_type=EvidenceAtomSupportType.DIRECT,
                factual_statement=(
                    "Built an analytical Python workflow, checked data quality, "
                    "and communicated appropriately bounded findings."
                ),
                supported_tools=["Python"],
                supported_methods=["analysis", "validation", "communication"],
                allowed_certainty=ClaimCertainty.OBSERVED,
                prohibited_expansions=["production deployment"],
            ),
        ],
        prohibited_claims=["production deployment"],
        generator_version="test-generator-v1",
        data_classification=ApplicationWritingDataClassification(
            profile_id="maya-demo",
            profile_name="Maya Chen",
            is_demo=is_demo,
            source=source,
        ),
    )


def _writing_output() -> ApplicationWritingOutput:
    output = ApplicationWritingOutput(
        job_understanding=JobUnderstandingOutput(
            role_family="Data Science",
            seniority="Intern",
            central_objective="Turn data into reliable decisions.",
            core_responsibilities=["Analyze data", "Communicate findings"],
            must_have_requirements=["Analytics"],
            preferred_requirements=[],
            technical_expectations=["Python"],
            communication_expectations=["Explain findings"],
            concrete_tools_requiring_direct_proof=["Python"],
            broad_semantic_concepts=["analytics", "reporting"],
        ),
        requirement_coverage=[
            RequirementCoverageItem(
                requirement="analytics",
                level=RequirementCoverageLevel.STRONGLY_SUPPORTED,
                explanation="The research workflow directly supports analysis.",
                evidence_reference_ids=["evidence-1"],
            )
        ],
        claim_plan=ClaimPlanOutput(
            primary_positioning="Scientific analyst who checks data quality.",
            primary_proof_memory_id="memory-1",
            supported_requirements=["analytics", "Python"],
            claims_not_to_make=["production deployment"],
            resume_strategy="Lead with the analytical workflow.",
            cover_letter_strategy="Connect disciplined analysis to the role.",
            snippet_strategy="Answer directly with one research example.",
            tone="Direct and professional",
        ),
        unsupported_requirements=[],
        positioning_summary=(
            "Analytical researcher who builds careful Python workflows."
        ),
        resume_bullet_groups=[
            ResumeBulletGroupOutput(
                memory_id="memory-1",
                heading="Scientific Data Research",
                bullets=[
                    ResumeBulletOutput(
                        text=(
                            "Built a Python analysis workflow to test a scientific "
                            "question and assess data quality before interpreting "
                            "results."
                        ),
                        evidence_reference_ids=["evidence-1"],
                    )
                ],
            )
        ],
        cover_letter=CoverLetterSectionsOutput(
            opening="I am applying for the Data Science Intern role.",
            primary_evidence="My research required careful analysis and validation.",
            secondary_evidence="I learned to explain uncertain findings clearly.",
            closing="I would welcome the opportunity to contribute.",
            full_text=(
                "I am applying for the Data Science Intern role.\n\n"
                "My research required careful analysis and validation.\n\n"
                "I learned to explain uncertain findings clearly.\n\n"
                "I would welcome the opportunity to contribute."
            ),
            evidence_reference_ids=["evidence-1"],
        ),
        application_snippets=[
            ApplicationSnippetOutput(
                question_id="motivation",
                answer="I want to apply careful analysis to practical decisions.",
                evidence_reference_ids=["evidence-1"],
                evidence_atom_ids=["atom-memory-1-workflow"],
                tools_claimed=[],
                outcome_claimed=None,
                certainty=ClaimCertainty.OBSERVED,
            ),
            ApplicationSnippetOutput(
                question_id="complex-data-project",
                answer="I built an analytical workflow in Python.",
                evidence_reference_ids=["evidence-1"],
                evidence_atom_ids=["atom-memory-1-workflow"],
                tools_claimed=["Python"],
                outcome_claimed=None,
                certainty=ClaimCertainty.OBSERVED,
            ),
            ApplicationSnippetOutput(
                question_id="quality-reliability",
                answer="I explain uncertain findings clearly.",
                evidence_reference_ids=["evidence-1"],
                evidence_atom_ids=["atom-memory-1-workflow"],
                tools_claimed=[],
                outcome_claimed=None,
                certainty=ClaimCertainty.OBSERVED,
            ),
        ],
        evidence_references_used=[
            EvidenceReferenceUsed(
                evidence_reference_id="evidence-1",
                memory_id="memory-1",
                usage="Supports the research workflow claim.",
            )
        ],
        strategy_notes=["Prioritized the strongest analytical example."],
        quality_review_notes=["Writing is concise and evidence-backed."],
    )
    atom_ids = ["atom-memory-1-workflow"]
    target_atom_ids = ["atom-target-role"]
    claims = [
        CandidateFacingClaim(
            field_path="positioning_summary",
            claim_text=output.positioning_summary,
            evidence_atom_ids=atom_ids,
            claim_type=CandidateClaimType.POSITIONING,
            tools_claimed=["Python"],
            certainty=ClaimCertainty.OBSERVED,
        ),
        CandidateFacingClaim(
            field_path="resume_bullet_groups.0.bullets.0.text",
            claim_text=output.resume_bullet_groups[0].bullets[0].text,
            evidence_atom_ids=atom_ids,
            claim_type=CandidateClaimType.RESUME_BULLET,
            tools_claimed=["Python"],
            certainty=ClaimCertainty.OBSERVED,
        ),
        *[
            CandidateFacingClaim(
                field_path=f"cover_letter.{field}",
                claim_text=getattr(output.cover_letter, field),
                evidence_atom_ids=(
                    target_atom_ids if field in {"opening", "closing"} else atom_ids
                ),
                claim_type=CandidateClaimType.COVER_LETTER,
                certainty=(
                    ClaimCertainty.ASPIRATIONAL
                    if field in {"opening", "closing"}
                    else ClaimCertainty.OBSERVED
                ),
            )
            for field in (
                "opening",
                "primary_evidence",
                "secondary_evidence",
                "closing",
            )
        ],
        *[
            CandidateFacingClaim(
                field_path=f"application_snippets.{index}.answer",
                claim_text=snippet.answer,
                evidence_atom_ids=atom_ids,
                claim_type=CandidateClaimType.APPLICATION_ANSWER,
                tools_claimed=["Python"] if index == 1 else [],
                certainty=ClaimCertainty.OBSERVED,
            )
            for index, snippet in enumerate(output.application_snippets)
        ],
    ]
    return output.model_copy(update={"candidate_claims": claims})


class _FakeResponses:
    def __init__(self, results: list[Any]) -> None:
        self.results = results
        self.calls: list[dict[str, Any]] = []

    def parse(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class _FakeClient:
    def __init__(self, results: list[Any]) -> None:
        self.responses = _FakeResponses(results)


def _response(
    output: Any | None,
    *,
    request_id: str = "resp_test",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=request_id,
        output_parsed=output,
        output=[],
        usage=SimpleNamespace(
            input_tokens=210,
            output_tokens=480,
            input_tokens_details=SimpleNamespace(cached_tokens=30),
        ),
    )


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "application_writer_provider": "openai",
        "application_writer_data_policy": "demo-shared",
        "openai_api_key": "test-only-placeholder",
        "openai_application_writer_model": "gpt-5.6-terra",
        "openai_application_enable_review_pass": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_strict_input_and_output_schemas_reject_extra_fields() -> None:
    input_payload = _writing_input().model_dump()
    input_payload["raw_uploaded_document"] = "must not cross provider boundary"
    with pytest.raises(ValidationError):
        ApplicationWritingInput.model_validate(input_payload)

    output_payload = _writing_output().model_dump()
    output_payload["hidden_chain_of_thought"] = "not allowed"
    with pytest.raises(ValidationError):
        ApplicationWritingOutput.model_validate(output_payload)


def test_v3_schemas_expose_explicit_questions_and_answer_metadata() -> None:
    input_schema = ApplicationWritingInput.model_json_schema()
    output_schema = ApplicationWritingOutput.model_json_schema()

    assert _writing_input().schema_version == "application-writing-input-v3"
    assert _writing_output().schema_version == "application-writing-output-v3"
    assert set(input_schema["$defs"]["ApplicationQuestionInput"]["properties"]) == {
        "question_id",
        "question_text",
        "required",
        "maximum_length",
        "response_type",
        "relevant_target_requirement_ids",
    }
    assert set(output_schema["$defs"]["ApplicationSnippetOutput"]["properties"]) == {
        "question_id",
        "answer",
        "evidence_reference_ids",
        "evidence_atom_ids",
        "tools_claimed",
        "outcome_claimed",
        "certainty",
        "validation_metadata",
    }


def test_local_provider_requires_no_api_key_and_records_safe_metadata() -> None:
    provider = LocalDeterministicApplicationWritingProvider(
        lambda writing_input: _writing_output()
    )

    result = provider.generate_application_draft(_writing_input(is_demo=False))

    assert result.provider_metadata.provider == "local-deterministic"
    assert result.provider_metadata.model == "local-deterministic"
    assert result.provider_metadata.input_tokens is None


def test_openai_provider_uses_responses_parse_strict_schema_and_store_false() -> None:
    client = _FakeClient([_response(_writing_output())])
    provider = OpenAIApplicationWritingProvider(_settings(), client=client)

    result = provider.generate_application_draft(_writing_input())

    call = client.responses.calls[0]
    assert call["model"] == "gpt-5.6-terra"
    assert call["text_format"] is ApplicationWritingOutput
    assert call["store"] is False
    assert len(client.responses.calls) == 1
    assert result.provider_metadata.request_id == "resp_test"
    assert result.provider_metadata.input_tokens == 210
    assert result.provider_metadata.cached_input_tokens == 30
    assert result.provider_metadata.output_tokens == 480
    assert "test-only-placeholder" not in str(call)
    request_payload = json.loads(call["input"][1]["content"])
    assert [
        question["question_id"]
        for question in request_payload["application_questions"]
    ] == ["motivation", "complex-data-project", "quality-reliability"]


def test_two_of_three_answers_get_one_targeted_repair_without_rewriting_package() -> (
    None
):
    complete = _writing_output()
    partial = complete.model_copy(
        update={
            "application_snippets": [
                complete.application_snippets[0],
                complete.application_snippets[2],
            ]
        }
    )
    repair = ApplicationAnswerRepairOutput(
        application_snippets=[complete.application_snippets[1]]
    )
    client = _FakeClient(
        [
            _response(partial, request_id="resp_two_of_three"),
            _response(repair, request_id="resp_targeted_repair"),
        ]
    )
    provider = OpenAIApplicationWritingProvider(_settings(), client=client)
    resume_before = partial.resume_bullet_groups[0].model_dump(mode="json")
    cover_before = partial.cover_letter.model_dump(mode="json")

    result = provider.generate_application_draft(_writing_input())

    assert [item.question_id for item in result.application_snippets] == [
        "motivation",
        "complex-data-project",
        "quality-reliability",
    ]
    assert result.resume_bullet_groups[0].model_dump(mode="json") == resume_before
    assert result.cover_letter.model_dump(mode="json") == cover_before
    assert len(client.responses.calls) == 2
    repair_call = client.responses.calls[1]
    assert repair_call["text_format"] is ApplicationAnswerRepairOutput
    assert repair_call["store"] is False
    repair_payload = json.loads(repair_call["input"][1]["content"])
    assert set(repair_payload) == {
        "missing_questions",
        "existing_valid_package_sections",
        "relevant_evidence_atoms",
        "prohibited_claims",
        "strict_answer_schema",
    }
    assert repair_payload["missing_questions"] == [
        {
            "question_id": "complex-data-project",
            "question_text": "Describe a project where you analyzed complex data.",
        }
    ]
    assert result.validation_metadata.repairs[0].code == (
        "MISSING_REQUIRED_APPLICATION_ANSWER"
    )


def test_failed_targeted_answer_repair_is_not_retried_or_merged() -> None:
    complete = _writing_output()
    partial = complete.model_copy(
        update={"application_snippets": complete.application_snippets[:2]}
    )
    client = _FakeClient(
        [
            _response(partial),
            _response(ApplicationAnswerRepairOutput(application_snippets=[])),
        ]
    )
    provider = OpenAIApplicationWritingProvider(_settings(), client=client)

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        provider.generate_application_draft(_writing_input())

    assert len(client.responses.calls) == 2
    assert caught.value.validation_diagnostic is not None
    assert caught.value.validation_diagnostic.validation_rule_code is (
        ApplicationWritingValidationCode.MISSING_REQUIRED_APPLICATION_ANSWER
    )


@pytest.mark.parametrize(
    ("updates", "expected_code"),
    [
        (
            {
                "answer": "I built an analytical Python workflow on AWS.",
                "tools_claimed": ["Python", "AWS"],
            },
            ApplicationWritingValidationCode.UNSUPPORTED_CONCRETE_TOOL,
        ),
        (
            {"evidence_atom_ids": ["atom-unknown"]},
            ApplicationWritingValidationCode.UNKNOWN_EVIDENCE_REFERENCE,
        ),
    ],
)
def test_targeted_repair_cannot_bypass_tool_or_evidence_validation(
    updates: dict[str, object],
    expected_code: ApplicationWritingValidationCode,
) -> None:
    complete = _writing_output()
    partial = complete.model_copy(
        update={
            "application_snippets": [
                complete.application_snippets[0],
                complete.application_snippets[2],
            ]
        }
    )
    invalid_answer = complete.application_snippets[1].model_copy(update=updates)
    client = _FakeClient(
        [
            _response(partial),
            _response(
                ApplicationAnswerRepairOutput(
                    application_snippets=[invalid_answer]
                )
            ),
        ]
    )
    provider = OpenAIApplicationWritingProvider(_settings(), client=client)

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        provider.generate_application_draft(_writing_input())

    assert caught.value.validation_diagnostic is not None
    assert caught.value.validation_diagnostic.validation_rule_code is expected_code


def test_factual_application_answers_require_both_evidence_id_layers() -> None:
    for field in ("evidence_reference_ids", "evidence_atom_ids"):
        output = _writing_output()
        snippets = list(output.application_snippets)
        snippets[1] = snippets[1].model_copy(update={field: []})
        output = output.model_copy(update={"application_snippets": snippets})
        if field == "evidence_atom_ids":
            output = output.model_copy(
                update={
                    "candidate_claims": [
                        claim.model_copy(update={"evidence_atom_ids": []})
                        if claim.field_path == "application_snippets.1.answer"
                        else claim
                        for claim in output.candidate_claims
                    ]
                }
            )

        with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
            validate_application_writing_output_contract(_writing_input(), output)

        assert caught.value.validation_diagnostic is not None
        assert caught.value.validation_diagnostic.validation_rule_code is (
            ApplicationWritingValidationCode.UNKNOWN_EVIDENCE_REFERENCE
        )


def test_openai_sdk_client_disables_implicit_http_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_openai(**kwargs: Any) -> _FakeClient:
        captured.update(kwargs)
        return _FakeClient([])

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=fake_openai))

    OpenAIApplicationWritingProvider(_settings())

    assert captured["max_retries"] == 0
    assert captured["timeout"] == 120.0


def test_openai_input_limit_rejects_before_provider_call() -> None:
    client = _FakeClient([_response(_writing_output())])
    provider = OpenAIApplicationWritingProvider(
        _settings(openai_application_max_input_characters=10_000),
        client=client,
    )

    with pytest.raises(ApplicationWritingDataPolicyError) as caught:
        provider.generate_application_draft(
            _writing_input(job_description="analysis " * 2_000)
        )

    assert caught.value.code == "data-policy"
    assert client.responses.calls == []


def test_malformed_output_gets_at_most_one_repair_attempt() -> None:
    client = _FakeClient([_response(None), _response(None)])
    provider = OpenAIApplicationWritingProvider(_settings(), client=client)

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        provider.generate_application_draft(_writing_input())

    assert caught.value.code == "malformed-output"
    assert len(client.responses.calls) == 2
    assert "Schema repair attempt" in client.responses.calls[1]["input"][-1]["content"]


def test_refusal_is_typed_and_is_not_retried() -> None:
    refusal = SimpleNamespace(
        output=[
            SimpleNamespace(
                content=[SimpleNamespace(type="refusal", refusal="cannot comply")]
            )
        ],
        output_parsed=None,
    )
    client = _FakeClient([refusal])
    provider = OpenAIApplicationWritingProvider(_settings(), client=client)

    with pytest.raises(ApplicationWritingRefusalError):
        provider.generate_application_draft(_writing_input())

    assert len(client.responses.calls) == 1


def test_authentication_failure_is_safe_typed_and_not_retried() -> None:
    class AuthenticationError(Exception):
        status_code = 401

    client = _FakeClient([AuthenticationError("request included private diagnostics")])
    provider = OpenAIApplicationWritingProvider(_settings(), client=client)

    with pytest.raises(ApplicationWritingAuthenticationError) as caught:
        provider.generate_application_draft(_writing_input())

    assert caught.value.code == "authentication"
    assert "private diagnostics" not in caught.value.safe_message
    assert len(client.responses.calls) == 1


@pytest.mark.parametrize(
    ("error", "expected_type", "expected_code"),
    [
        (
            type("BillingLimitError", (Exception,), {"status_code": 429})(
                "insufficient_quota: add billing credit"
            ),
            ApplicationWritingBillingError,
            "billing",
        ),
        (
            type("RateLimitError", (Exception,), {"status_code": 429})(
                "rate limit reached"
            ),
            ApplicationWritingRateLimitError,
            "rate-limit",
        ),
        (
            TimeoutError("provider timed out with internal details"),
            ApplicationWritingTimeoutError,
            "timeout",
        ),
        (
            type("InternalServerError", (Exception,), {"status_code": 500})(
                "provider internal diagnostics"
            ),
            ApplicationWritingRemoteProviderError,
            "provider-error",
        ),
    ],
)
def test_remote_failures_are_safe_typed_and_not_implicitly_retried(
    error: Exception,
    expected_type: type[Exception],
    expected_code: str,
) -> None:
    client = _FakeClient([error])
    provider = OpenAIApplicationWritingProvider(_settings(), client=client)

    with pytest.raises(expected_type) as caught:
        provider.generate_application_draft(_writing_input())

    assert getattr(caught.value, "code") == expected_code
    assert "internal diagnostics" not in str(caught.value)
    assert len(client.responses.calls) == 1


def test_missing_key_has_actionable_configuration_error_without_client_creation() -> (
    None
):
    with pytest.raises(ApplicationWritingConfigurationError) as caught:
        OpenAIApplicationWritingProvider(
            _settings(openai_api_key=None), client=_FakeClient([])
        )

    assert caught.value.code == "missing-api-key"
    assert "OPENAI_API_KEY" in caught.value.safe_message


def test_demo_shared_rejects_personal_profile_before_provider_call() -> None:
    client = _FakeClient([_response(_writing_output())])
    provider = OpenAIApplicationWritingProvider(_settings(), client=client)

    with pytest.raises(ApplicationWritingDataPolicyError) as caught:
        provider.generate_application_draft(
            _writing_input(is_demo=False, source=ApplicationWritingDataSource.PERSONAL)
        )

    assert "shared demo project" in caught.value.safe_message
    assert not client.responses.calls


@pytest.mark.parametrize(
    "identifier",
    [
        "Contact maya@example.com",
        "Call (512) 555-0198",
        "Mail to 123 Example Street",
        "SSN 123-45-6789",
        "api_key=sk-exampleplaceholder123456789",
    ],
)
def test_demo_shared_rejects_obvious_identifiers_and_secrets(identifier: str) -> None:
    with pytest.raises(ApplicationWritingDataPolicyError):
        validate_application_writing_data_policy(
            _writing_input(job_description=identifier),
            ApplicationWriterDataPolicy.DEMO_SHARED,
        )


def test_private_policy_permits_personal_profile_but_still_rejects_secrets() -> None:
    personal = _writing_input(
        is_demo=False,
        source=ApplicationWritingDataSource.PERSONAL,
        job_description="Contact analyst@example.com about the role.",
    )
    validate_application_writing_data_policy(
        personal, ApplicationWriterDataPolicy.PRIVATE
    )

    secret = personal.model_copy(
        update={"job_description": "password=do-not-send-this-value"}
    )
    with pytest.raises(ApplicationWritingDataPolicyError):
        validate_application_writing_data_policy(
            secret, ApplicationWriterDataPolicy.PRIVATE
        )


def test_optional_review_failure_preserves_valid_terra_draft() -> None:
    client = _FakeClient([_response(_writing_output()), TimeoutError("late")])
    provider = OpenAIApplicationWritingProvider(
        _settings(
            openai_application_enable_review_pass=True,
            openai_application_review_model="gpt-5.6-sol",
        ),
        client=client,
    )

    result = provider.generate_application_draft(_writing_input())

    assert result.positioning_summary == _writing_output().positioning_summary
    assert result.provider_metadata.review_pass_ran is False
    assert result.provider_metadata.review_error_code == "timeout"
    assert result.quality_review_notes[-1] == "Optional review pass unavailable."
    review_call = client.responses.calls[1]
    assert review_call["store"] is False
    review_payload = review_call["input"][1]["content"]
    assert '"selected_memories"' in review_payload
    assert '"validation_notes"' in review_payload


def test_successful_review_preserves_recorded_terra_repairs() -> None:
    terra = _writing_output()
    warning = " (Kubernetes is unsupported.)"
    terra.resume_bullet_groups[0].bullets[0].text += warning
    terra_claim = next(
        claim
        for claim in terra.candidate_claims
        if claim.field_path == "resume_bullet_groups.0.bullets.0.text"
    )
    terra_claim.claim_text += warning
    terra_claim.tools_claimed.append("Kubernetes")
    client = _FakeClient(
        [
            _response(terra, request_id="resp_terra"),
            _response(_writing_output(), request_id="resp_review"),
        ]
    )
    provider = OpenAIApplicationWritingProvider(
        _settings(
            openai_application_enable_review_pass=True,
            openai_application_review_model="gpt-5.6-sol",
        ),
        client=client,
    )

    result = provider.generate_application_draft(_writing_input())

    assert result.provider_metadata.review_pass_ran is True
    assert len(result.validation_metadata.repairs) == 1
    repair = result.validation_metadata.repairs[0]
    assert repair.code == "REMOVE_OPTIONAL_UNSUPPORTED_WARNING"
    assert repair.field_path == "resume_bullet_groups.0.bullets.0.text"
