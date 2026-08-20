"""Offline tests for the gated fictional-data live smoke harness."""

from __future__ import annotations

from io import StringIO
from typing import Any

from app.core.config import Settings
from app.fixtures.application_writing_demo import (
    build_maya_chen_demo_writing_input,
)
from app.services.application_writing_provider import (
    ApplicationSnippetOutput,
    ApplicationWritingErrorCode,
    ApplicationWritingInput,
    ApplicationWritingMalformedOutputError,
    ApplicationWritingOutput,
    ApplicationWritingProviderMetadata,
    ApplicationWritingRemoteProviderError,
    ApplicationWritingValidationCode,
    ApplicationWritingValidationDiagnostic,
    CandidateClaimType,
    CandidateFacingClaim,
    ClaimCertainty,
    ClaimPlanOutput,
    CoverLetterSectionsOutput,
    EvidenceReferenceUsed,
    JobUnderstandingOutput,
    RequirementCoverageItem,
    RequirementCoverageLevel,
    ResumeBulletGroupOutput,
    ResumeBulletOutput,
    UnsupportedClaimCandidate,
    UnsupportedRequirementOutput,
)
from scripts.live_application_writer_smoke import run_smoke


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "run_live_openai_tests": True,
        "application_writer_provider": "openai",
        "application_writer_data_policy": "demo-shared",
        "openai_api_key": "test-only-secret-placeholder",
        "openai_application_writer_model": "gpt-5.6-terra",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _valid_output() -> ApplicationWritingOutput:
    positioning = (
        "Scientific analyst who builds reproducible Python workflows and "
        "communicates appropriately bounded findings."
    )
    resume_bullet = (
        "Built a reproducible Python workflow to join scientific datasets, evaluate "
        "a research question, and check uncertainty before interpreting the result."
    )
    cover_letter = CoverLetterSectionsOutput(
        opening="I am applying for the Data Science Intern role.",
        primary_evidence=(
            "My scientific research required reproducible analysis and careful "
            "validation before I interpreted the result."
        ),
        secondary_evidence=(
            "A separate image-quality project refined my approach to ambiguous cases "
            "and consistent review."
        ),
        closing="I would welcome the opportunity to contribute those habits.",
        full_text=" ".join(
            [
                "I am applying for the Data Science Intern role.",
                (
                    "My scientific research required reproducible analysis and careful "
                    "validation before I interpreted the result."
                ),
                (
                    "A separate image-quality project refined my approach to ambiguous "
                    "cases and consistent review."
                ),
                "I would welcome the opportunity to contribute those habits.",
            ]
        ),
        evidence_reference_ids=[
            "demo-evidence-analysis-workflow",
            "demo-evidence-uncertainty-review",
            "demo-evidence-image-quality",
        ],
    )
    snippets = [
        ApplicationSnippetOutput(
            question_id="motivation",
            answer=(
                "I am drawn to work that connects reproducible analysis with careful "
                "decisions."
            ),
            evidence_reference_ids=["demo-evidence-analysis-workflow"],
            evidence_atom_ids=["atom-scientific-python-workflow"],
            tools_claimed=[],
            outcome_claimed=None,
            certainty=ClaimCertainty.ASPIRATIONAL,
        ),
        ApplicationSnippetOutput(
            question_id="complex-data-project",
            answer=(
                "I built a reproducible Python workflow and checked uncertainty before "
                "interpreting the result."
            ),
            evidence_reference_ids=[
                "demo-evidence-analysis-workflow",
                "demo-evidence-uncertainty-review",
            ],
            evidence_atom_ids=[
                "atom-scientific-python-workflow",
                "atom-scientific-uncertainty",
            ],
            tools_claimed=["Python"],
            outcome_claimed=None,
            certainty=ClaimCertainty.QUALIFIED,
        ),
        ApplicationSnippetOutput(
            question_id="quality-reliability",
            answer=(
                "I flag ambiguous cases for review instead of forcing an unsupported "
                "category."
            ),
            evidence_reference_ids=["demo-evidence-image-quality"],
            evidence_atom_ids=[
                "atom-image-quality-process",
                "atom-enrichment-quality-decisions",
            ],
            tools_claimed=[],
            outcome_claimed=None,
            certainty=ClaimCertainty.QUALIFIED,
        ),
    ]
    return ApplicationWritingOutput(
        job_understanding=JobUnderstandingOutput(
            role_family="Data Science",
            seniority="Intern",
            central_objective="Turn complex data into reliable findings.",
            core_responsibilities=["Analyze data", "Explain findings"],
            must_have_requirements=["data analysis", "communication"],
            preferred_requirements=["SQL"],
            technical_expectations=["Python", "data quality"],
            communication_expectations=["Explain results"],
            concrete_tools_requiring_direct_proof=["Python", "SQL", "AWS"],
            broad_semantic_concepts=["analytics", "reporting"],
        ),
        requirement_coverage=[
            RequirementCoverageItem(
                requirement="data analysis",
                level=RequirementCoverageLevel.STRONGLY_SUPPORTED,
                explanation="The scientific workflow provides direct proof.",
                evidence_reference_ids=["demo-evidence-analysis-workflow"],
            )
        ],
        claim_plan=ClaimPlanOutput(
            primary_positioning="A careful analyst and clear communicator.",
            primary_proof_memory_id="demo-memory-scientific-analysis",
            secondary_proof_memory_ids=["demo-memory-image-quality"],
            supported_requirements=["data analysis", "Python"],
            partially_supported_requirements=["reporting"],
            unsupported_requirements=["SQL", "cloud"],
            claims_not_to_make=["SQL experience", "cloud deployment"],
            missing_evidence=["Direct SQL work"],
            resume_strategy="Lead with analysis and validation.",
            cover_letter_strategy="Connect careful research to reliable decisions.",
            snippet_strategy="Use one direct scientific-analysis example.",
            tone="Direct and professional",
        ),
        unsupported_requirements=[
            UnsupportedRequirementOutput(
                requirement="SQL",
                explanation="The selected evidence does not prove SQL experience.",
            ),
            UnsupportedRequirementOutput(
                requirement="cloud deployment",
                explanation=(
                    "The selected evidence does not prove cloud deployment experience."
                ),
            ),
        ],
        positioning_summary=positioning,
        resume_bullet_groups=[
            ResumeBulletGroupOutput(
                memory_id="demo-memory-scientific-analysis",
                heading="Scientific Data Research Project",
                bullets=[
                    ResumeBulletOutput(
                        text=resume_bullet,
                        evidence_reference_ids=[
                            "demo-evidence-analysis-workflow",
                            "demo-evidence-uncertainty-review",
                        ],
                    )
                ],
            )
        ],
        cover_letter=cover_letter,
        application_snippets=snippets,
        evidence_references_used=[
            EvidenceReferenceUsed(
                evidence_reference_id="demo-evidence-analysis-workflow",
                memory_id="demo-memory-scientific-analysis",
                usage="Supports the reproducible Python workflow.",
            ),
            EvidenceReferenceUsed(
                evidence_reference_id="demo-evidence-uncertainty-review",
                memory_id="demo-memory-scientific-analysis",
                usage="Supports uncertainty review in the resume bullet.",
            ),
            EvidenceReferenceUsed(
                evidence_reference_id="demo-evidence-image-quality",
                memory_id="demo-memory-image-quality",
                usage="Supports the data-quality review example.",
            ),
        ],
        candidate_claims=[
            CandidateFacingClaim(
                field_path="positioning_summary",
                claim_text=positioning,
                evidence_atom_ids=["atom-scientific-python-workflow"],
                claim_type=CandidateClaimType.POSITIONING,
                tools_claimed=["Python"],
                certainty=ClaimCertainty.QUALIFIED,
            ),
            CandidateFacingClaim(
                field_path="resume_bullet_groups.0.bullets.0.text",
                claim_text=resume_bullet,
                evidence_atom_ids=[
                    "atom-scientific-python-workflow",
                    "atom-scientific-uncertainty",
                ],
                claim_type=CandidateClaimType.RESUME_BULLET,
                tools_claimed=["Python"],
                certainty=ClaimCertainty.QUALIFIED,
            ),
            CandidateFacingClaim(
                field_path="cover_letter.opening",
                claim_text=cover_letter.opening,
                evidence_atom_ids=["atom-target-role"],
                claim_type=CandidateClaimType.COVER_LETTER,
                certainty=ClaimCertainty.ASPIRATIONAL,
            ),
            CandidateFacingClaim(
                field_path="cover_letter.primary_evidence",
                claim_text=cover_letter.primary_evidence,
                evidence_atom_ids=[
                    "atom-scientific-python-workflow",
                    "atom-scientific-uncertainty",
                ],
                claim_type=CandidateClaimType.COVER_LETTER,
                certainty=ClaimCertainty.QUALIFIED,
            ),
            CandidateFacingClaim(
                field_path="cover_letter.secondary_evidence",
                claim_text=cover_letter.secondary_evidence,
                evidence_atom_ids=[
                    "atom-image-quality-process",
                    "atom-enrichment-quality-decisions",
                ],
                claim_type=CandidateClaimType.COVER_LETTER,
                certainty=ClaimCertainty.QUALIFIED,
            ),
            CandidateFacingClaim(
                field_path="cover_letter.closing",
                claim_text=cover_letter.closing,
                evidence_atom_ids=["atom-target-role"],
                claim_type=CandidateClaimType.COVER_LETTER,
                certainty=ClaimCertainty.ASPIRATIONAL,
            ),
            CandidateFacingClaim(
                field_path="application_snippets.0.answer",
                claim_text=snippets[0].answer,
                evidence_atom_ids=["atom-scientific-python-workflow"],
                claim_type=CandidateClaimType.APPLICATION_ANSWER,
                certainty=ClaimCertainty.ASPIRATIONAL,
            ),
            CandidateFacingClaim(
                field_path="application_snippets.1.answer",
                claim_text=snippets[1].answer,
                evidence_atom_ids=[
                    "atom-scientific-python-workflow",
                    "atom-scientific-uncertainty",
                ],
                claim_type=CandidateClaimType.APPLICATION_ANSWER,
                tools_claimed=["Python"],
                certainty=ClaimCertainty.QUALIFIED,
            ),
            CandidateFacingClaim(
                field_path="application_snippets.2.answer",
                claim_text=snippets[2].answer,
                evidence_atom_ids=[
                    "atom-image-quality-process",
                    "atom-enrichment-quality-decisions",
                ],
                claim_type=CandidateClaimType.APPLICATION_ANSWER,
                certainty=ClaimCertainty.QUALIFIED,
            ),
        ],
        strategy_notes=["Prioritized direct proof."],
        quality_review_notes=["Concise and evidence-backed."],
        provider_metadata=ApplicationWritingProviderMetadata(
            provider="openai",
            model="gpt-5.6-terra",
            request_id="resp_demo",
            input_tokens=350,
            cached_input_tokens=20,
            output_tokens=700,
            latency_ms=1250,
        ),
    )


def _update_candidate_claim(
    output: ApplicationWritingOutput,
    field_path: str,
    **updates: Any,
) -> ApplicationWritingOutput:
    claims = [
        claim.model_copy(update=updates) if claim.field_path == field_path else claim
        for claim in output.candidate_claims
    ]
    assert sum(claim.field_path == field_path for claim in claims) == 1
    return output.model_copy(update={"candidate_claims": claims})


class _FakeProvider:
    def __init__(self, result: ApplicationWritingOutput | Exception) -> None:
        self.name = "fake-openai"
        self.result = result
        self.calls: list[ApplicationWritingInput] = []

    def generate_application_draft(
        self, writing_input: ApplicationWritingInput
    ) -> ApplicationWritingOutput:
        self.calls.append(writing_input)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_maya_fixture_is_pure_seeded_demo_with_complete_context() -> None:
    fixture = build_maya_chen_demo_writing_input()
    serialized = fixture.model_dump_json()

    assert fixture.data_classification.is_demo is True
    assert fixture.data_classification.source == "seeded-fictional"
    assert len(fixture.selected_memories) == 3
    assert fixture.approved_enrichment
    assert fixture.proof_artifacts
    assert fixture.missing_proof_warnings
    assert [question.question_id for question in fixture.application_questions] == [
        "motivation",
        "complex-data-project",
        "quality-reliability",
    ]
    assert [question.question_text for question in fixture.application_questions] == [
        "Why are you interested in this Data Science internship?",
        "Describe a project where you analyzed complex data.",
        "Describe how you ensured the quality or reliability of your work.",
    ]
    assert all(question.required for question in fixture.application_questions)
    assert "Maya Chen" in serialized
    assert "Arnav" not in serialized
    assert "@" not in serialized


def test_disabled_gate_exits_without_constructing_or_calling_provider() -> None:
    constructed = False

    def provider_factory(settings: Settings) -> _FakeProvider:
        nonlocal constructed
        constructed = True
        return _FakeProvider(_valid_output())

    stdout = StringIO()
    exit_code = run_smoke(
        settings=_settings(run_live_openai_tests=False),
        provider_factory=provider_factory,
        stdout=stdout,
    )

    assert exit_code == 2
    assert constructed is False
    assert "RUN_LIVE_OPENAI_TESTS=true" in stdout.getvalue()


def test_data_policy_gate_exits_without_provider_call() -> None:
    provider = _FakeProvider(_valid_output())
    stdout = StringIO()

    exit_code = run_smoke(
        settings=_settings(application_writer_data_policy="private"),
        provider_factory=lambda settings: provider,
        stdout=stdout,
    )

    assert exit_code == 2
    assert provider.calls == []
    assert "demo-shared" in stdout.getvalue()


def test_provider_and_terra_model_gates_exit_without_provider_call() -> None:
    provider = _FakeProvider(_valid_output())

    wrong_provider_exit = run_smoke(
        settings=_settings(application_writer_provider="local-deterministic"),
        provider_factory=lambda settings: provider,
        stdout=StringIO(),
    )
    wrong_model_exit = run_smoke(
        settings=_settings(openai_application_writer_model="gpt-5.6-sol"),
        provider_factory=lambda settings: provider,
        stdout=StringIO(),
    )

    assert wrong_provider_exit == 2
    assert wrong_model_exit == 2
    assert provider.calls == []


def test_success_calls_provider_once_and_prints_only_safe_summary() -> None:
    provider = _FakeProvider(_valid_output())
    stdout = StringIO()

    exit_code = run_smoke(
        settings=_settings(),
        provider_factory=lambda settings: provider,
        stdout=stdout,
    )

    rendered = stdout.getvalue()
    fixture = build_maya_chen_demo_writing_input()
    assert exit_code == 0
    assert len(provider.calls) == 1
    assert [
        question.question_id
        for question in provider.calls[0].application_questions
    ] == ["motivation", "complex-data-project", "quality-reliability"]
    output_question_ids = [
        snippet.question_id for snippet in _valid_output().application_snippets
    ]
    assert output_question_ids == [
        "motivation",
        "complex-data-project",
        "quality-reliability",
    ]
    assert all(
        snippet.evidence_reference_ids
        and snippet.evidence_atom_ids
        and snippet.outcome_claimed is None
        for snippet in _valid_output().application_snippets
    )
    assert "PASS" in rendered
    assert "model: gpt-5.6-terra" in rendered
    assert "validation: PASS" in rendered
    assert "input_tokens: 350" in rendered
    assert "test-only-secret-placeholder" not in rendered
    assert fixture.job_description not in rendered
    assert _valid_output().cover_letter.full_text not in rendered


def test_provider_failure_has_nonzero_exit_and_safe_error_only() -> None:
    provider = _FakeProvider(
        ApplicationWritingRemoteProviderError(
            ApplicationWritingErrorCode.PROVIDER,
            "OpenAI could not complete the application-writing request.",
        )
    )
    stdout = StringIO()

    exit_code = run_smoke(
        settings=_settings(),
        provider_factory=lambda settings: provider,
        stdout=stdout,
    )

    rendered = stdout.getvalue()
    assert exit_code == 1
    assert len(provider.calls) == 1
    assert "provider-error" in rendered
    assert "test-only-secret-placeholder" not in rendered


def test_validation_failure_is_nonzero_and_does_not_print_generated_claim() -> None:
    unsupported = "Invented confidential accomplishment"
    invalid = _valid_output().model_copy(
        update={
            "unsupported_claim_candidates": [
                UnsupportedClaimCandidate(
                    claim=unsupported,
                    reason="No supporting evidence.",
                    surface="cover-letter",
                )
            ]
        }
    )
    provider = _FakeProvider(invalid)
    stdout = StringIO()

    exit_code = run_smoke(
        settings=_settings(),
        provider_factory=lambda settings: provider,
        stdout=stdout,
    )

    assert exit_code == 1
    rendered = stdout.getvalue()
    assert "validation_rule_code: UNRESOLVED_UNSUPPORTED_CLAIM" in rendered
    assert unsupported not in rendered


def test_structured_validation_diagnostic_prints_only_allowlisted_fields() -> None:
    private_message = (
        "Full claim and provider response: used AWS with secret request context."
    )
    diagnostic = ApplicationWritingValidationDiagnostic(
        validation_rule_code=(
            ApplicationWritingValidationCode.UNSUPPORTED_CONCRETE_TOOL
        ),
        output_section="resume",
        field_path="resume_bullet_groups.0.bullets.0.text",
        normalized_disputed_phrase="aws",
        referenced_evidence_ids=["atom-scientific-python-workflow"],
        expected_evidence_category=(
            "direct evidence atom explicitly listing the capability"
        ),
        surface_classification="user-facing",
    )
    provider = _FakeProvider(
        ApplicationWritingMalformedOutputError(
            ApplicationWritingErrorCode.MALFORMED_OUTPUT,
            private_message,
            validation_diagnostic=diagnostic,
        )
    )
    stdout = StringIO()

    exit_code = run_smoke(
        settings=_settings(),
        provider_factory=lambda settings: provider,
        stdout=stdout,
    )

    assert exit_code == 1
    assert stdout.getvalue().splitlines() == [
        "validation_rule_code: UNSUPPORTED_CONCRETE_TOOL",
        "output_section: resume",
        "field_path: resume_bullet_groups.0.bullets.0.text",
        "normalized_disputed_phrase: aws",
        'referenced_evidence_ids: ["atom-scientific-python-workflow"]',
        (
            "expected_evidence_category: direct evidence atom explicitly listing "
            "the capability"
        ),
        "surface_classification: user-facing",
    ]
    assert private_message not in stdout.getvalue()
    assert "test-only-secret-placeholder" not in stdout.getvalue()


def test_analysis_only_unsupported_tool_is_allowed() -> None:
    valid = _valid_output()
    analysis_only = [
        *valid.unsupported_requirements,
        UnsupportedRequirementOutput(
            requirement="Kubernetes",
            explanation=(
                "The target requests Kubernetes, but selected evidence does not "
                "support claiming it."
            ),
        ),
    ]
    provider = _FakeProvider(
        valid.model_copy(update={"unsupported_requirements": analysis_only})
    )
    stdout = StringIO()

    exit_code = run_smoke(
        settings=_settings(),
        provider_factory=lambda settings: provider,
        stdout=stdout,
    )

    assert exit_code == 0
    assert "validation: PASS" in stdout.getvalue()


def test_candidate_tool_is_blocked_with_safe_field_diagnostic() -> None:
    invalid_claim = (
        "Built a reproducible Python workflow on AWS to evaluate scientific data."
    )
    valid = _valid_output()
    groups = list(valid.resume_bullet_groups)
    bullets = list(groups[0].bullets)
    bullets[0] = bullets[0].model_copy(update={"text": invalid_claim})
    groups[0] = groups[0].model_copy(update={"bullets": bullets})
    invalid = valid.model_copy(update={"resume_bullet_groups": groups})
    invalid = _update_candidate_claim(
        invalid,
        "resume_bullet_groups.0.bullets.0.text",
        claim_text=invalid_claim,
        tools_claimed=["Python", "AWS"],
    )
    provider = _FakeProvider(invalid)
    stdout = StringIO()

    exit_code = run_smoke(
        settings=_settings(),
        provider_factory=lambda settings: provider,
        stdout=stdout,
    )

    rendered = stdout.getvalue()
    assert exit_code == 1
    assert "validation_rule_code: UNSUPPORTED_CONCRETE_TOOL" in rendered
    assert "output_section: resume" in rendered
    assert "field_path: resume_bullet_groups.0.bullets.0.text" in rendered
    assert "normalized_disputed_phrase: aws" in rendered
    assert "surface_classification: user-facing" in rendered
    assert invalid_claim not in rendered


def test_invented_outcome_is_rejected_even_with_a_valid_evidence_reference() -> None:
    invented = "I earned an interview invitation through this project."
    valid = _valid_output()
    snippets = list(valid.application_snippets)
    snippets[0] = snippets[0].model_copy(
        update={"answer": invented, "certainty": ClaimCertainty.OBSERVED}
    )
    invalid = valid.model_copy(update={"application_snippets": snippets})
    invalid = _update_candidate_claim(
        invalid,
        "application_snippets.0.answer",
        claim_text=invented,
        certainty=ClaimCertainty.OBSERVED,
    )
    provider = _FakeProvider(invalid)
    stdout = StringIO()

    exit_code = run_smoke(
        settings=_settings(),
        provider_factory=lambda settings: provider,
        stdout=stdout,
    )

    assert exit_code == 1
    rendered = stdout.getvalue()
    assert "validation_rule_code: UNSUPPORTED_OUTCOME" in rendered
    assert invented not in rendered
