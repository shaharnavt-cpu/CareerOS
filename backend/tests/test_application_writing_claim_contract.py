"""Pure regressions for the application-writing claim contract."""

from __future__ import annotations

import pytest

from app.fixtures.application_writing_demo import (
    build_maya_chen_demo_writing_input,
)
from app.services.application_writing_provider import (
    ApplicationQuestionInput,
    ApplicationSnippetOutput,
    ApplicationWritingInput,
    ApplicationWritingMalformedOutputError,
    ApplicationWritingOutput,
    ApplicationWritingValidationCode,
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
    StructuredOutcome,
    UnsupportedRequirementOutput,
    sanitize_application_writing_output,
    validate_application_writing_output_contract,
)

SCIENTIFIC_MEMORY_ID = "demo-memory-scientific-analysis"
IMAGE_MEMORY_ID = "demo-memory-image-quality"
SCIENTIFIC_WORKFLOW_REF = "demo-evidence-analysis-workflow"
SCIENTIFIC_UNCERTAINTY_REF = "demo-evidence-uncertainty-review"
IMAGE_QUALITY_REF = "demo-evidence-image-quality"

POSITIONING_PATH = "positioning_summary"
RESUME_PATH = "resume_bullet_groups.0.bullets.0.text"
COVER_PRIMARY_PATH = "cover_letter.primary_evidence"
SNIPPET_PROJECT_PATH = "application_snippets.1.answer"


def _writing_input() -> ApplicationWritingInput:
    return build_maya_chen_demo_writing_input()


def _candidate_claim(
    *,
    field_path: str,
    claim_text: str,
    evidence_atom_ids: list[str],
    claim_type: CandidateClaimType,
    certainty: ClaimCertainty,
    tools_claimed: list[str] | None = None,
    outcome_claimed: StructuredOutcome | None = None,
) -> CandidateFacingClaim:
    return CandidateFacingClaim(
        field_path=field_path,
        claim_text=claim_text,
        evidence_atom_ids=evidence_atom_ids,
        claim_type=claim_type,
        tools_claimed=tools_claimed or [],
        outcome_claimed=outcome_claimed,
        certainty=certainty,
    )


def _valid_output(
    writing_input: ApplicationWritingInput | None = None,
) -> ApplicationWritingOutput:
    writing_input = writing_input or _writing_input()
    positioning = "Scientific analyst who builds reproducible Python workflows."
    resume = (
        "Built a reproducible Python workflow joining spectroscopy and imaging tables."
    )
    opening = "I am applying for the Data Science Intern role."
    primary = (
        "My scientific research used a reproducible Python workflow and careful "
        "validation."
    )
    secondary = (
        "A separate image-quality project used repeatable visual review and "
        "categorization."
    )
    closing = "I would welcome the opportunity to contribute these analytical habits."
    snippet_templates = {
        "motivation": {
            "answer": (
                "I want to apply careful analysis and validation to practical "
                "decisions."
            ),
            "evidence_reference_ids": [SCIENTIFIC_UNCERTAINTY_REF],
            "evidence_atom_ids": ["atom-scientific-uncertainty"],
            "tools_claimed": [],
            "certainty": ClaimCertainty.QUALIFIED,
        },
        "complex-data-project": {
            "answer": (
                "I built a reproducible Python workflow joining scientific datasets."
            ),
            "evidence_reference_ids": [SCIENTIFIC_WORKFLOW_REF],
            "evidence_atom_ids": ["atom-scientific-python-workflow"],
            "tools_claimed": ["Python"],
            "certainty": ClaimCertainty.OBSERVED,
        },
        "quality-reliability": {
            "answer": (
                "I flag ambiguous images for review instead of forcing uncertain "
                "labels."
            ),
            "evidence_reference_ids": [IMAGE_QUALITY_REF],
            "evidence_atom_ids": ["atom-enrichment-quality-decisions"],
            "tools_claimed": [],
            "certainty": ClaimCertainty.OBSERVED,
        },
    }
    fallback_template = snippet_templates["complex-data-project"]
    snippets = [
        ApplicationSnippetOutput(
            question_id=question.question_id,
            answer=str(
                snippet_templates.get(question.question_id, fallback_template)[
                    "answer"
                ]
            ),
            evidence_reference_ids=list(
                snippet_templates.get(question.question_id, fallback_template)[
                    "evidence_reference_ids"
                ]
            ),
            evidence_atom_ids=list(
                snippet_templates.get(question.question_id, fallback_template)[
                    "evidence_atom_ids"
                ]
            ),
            tools_claimed=list(
                snippet_templates.get(question.question_id, fallback_template)[
                    "tools_claimed"
                ]
            ),
            outcome_claimed=None,
            certainty=snippet_templates.get(question.question_id, fallback_template)[
                "certainty"
            ],
        )
        for question in writing_input.application_questions
        if question.required
    ]
    return ApplicationWritingOutput(
        job_understanding=JobUnderstandingOutput(
            role_family="Data Science",
            seniority="Intern",
            central_objective="Turn complex data into reliable findings.",
            core_responsibilities=["Analyze data", "Explain findings"],
            must_have_requirements=["data analysis", "communication"],
            preferred_requirements=["SQL", "cloud deployment"],
            technical_expectations=["Python", "SQL", "AWS"],
            communication_expectations=["Explain results"],
            concrete_tools_requiring_direct_proof=["Python", "SQL", "AWS"],
            broad_semantic_concepts=["analytics", "reporting"],
        ),
        requirement_coverage=[
            RequirementCoverageItem(
                requirement="data analysis",
                level=RequirementCoverageLevel.STRONGLY_SUPPORTED,
                explanation="The scientific workflow provides direct proof.",
                evidence_reference_ids=[SCIENTIFIC_WORKFLOW_REF],
            )
        ],
        claim_plan=ClaimPlanOutput(
            primary_positioning="A careful analyst and clear communicator.",
            primary_proof_memory_id=SCIENTIFIC_MEMORY_ID,
            secondary_proof_memory_ids=[IMAGE_MEMORY_ID],
            supported_requirements=["data analysis", "Python"],
            partially_supported_requirements=["reporting"],
            unsupported_requirements=["SQL", "cloud deployment"],
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
                explanation="The selected evidence does not prove deployment work.",
            ),
        ],
        positioning_summary=positioning,
        resume_bullet_groups=[
            ResumeBulletGroupOutput(
                memory_id=SCIENTIFIC_MEMORY_ID,
                heading="Scientific Data Research Project",
                bullets=[
                    ResumeBulletOutput(
                        text=resume,
                        evidence_reference_ids=[SCIENTIFIC_WORKFLOW_REF],
                    )
                ],
            )
        ],
        cover_letter=CoverLetterSectionsOutput(
            opening=opening,
            primary_evidence=primary,
            secondary_evidence=secondary,
            closing=closing,
            full_text=" ".join((opening, primary, secondary, closing)),
            evidence_reference_ids=[
                SCIENTIFIC_WORKFLOW_REF,
                SCIENTIFIC_UNCERTAINTY_REF,
                IMAGE_QUALITY_REF,
            ],
        ),
        application_snippets=snippets,
        evidence_references_used=[
            EvidenceReferenceUsed(
                evidence_reference_id=SCIENTIFIC_WORKFLOW_REF,
                memory_id=SCIENTIFIC_MEMORY_ID,
                usage="Supports the reproducible Python workflow.",
            ),
            EvidenceReferenceUsed(
                evidence_reference_id=SCIENTIFIC_UNCERTAINTY_REF,
                memory_id=SCIENTIFIC_MEMORY_ID,
                usage="Supports careful validation and uncertainty review.",
            ),
            EvidenceReferenceUsed(
                evidence_reference_id=IMAGE_QUALITY_REF,
                memory_id=IMAGE_MEMORY_ID,
                usage="Supports the image-quality review process.",
            ),
        ],
        candidate_claims=[
            _candidate_claim(
                field_path=POSITIONING_PATH,
                claim_text=positioning,
                evidence_atom_ids=["atom-scientific-python-workflow"],
                claim_type=CandidateClaimType.POSITIONING,
                tools_claimed=["Python"],
                certainty=ClaimCertainty.OBSERVED,
            ),
            _candidate_claim(
                field_path=RESUME_PATH,
                claim_text=resume,
                evidence_atom_ids=["atom-scientific-python-workflow"],
                claim_type=CandidateClaimType.RESUME_BULLET,
                tools_claimed=["Python"],
                certainty=ClaimCertainty.OBSERVED,
            ),
            _candidate_claim(
                field_path="cover_letter.opening",
                claim_text=opening,
                evidence_atom_ids=["atom-target-role"],
                claim_type=CandidateClaimType.COVER_LETTER,
                certainty=ClaimCertainty.ASPIRATIONAL,
            ),
            _candidate_claim(
                field_path=COVER_PRIMARY_PATH,
                claim_text=primary,
                evidence_atom_ids=[
                    "atom-scientific-python-workflow",
                    "atom-scientific-uncertainty",
                ],
                claim_type=CandidateClaimType.COVER_LETTER,
                tools_claimed=["Python"],
                certainty=ClaimCertainty.QUALIFIED,
            ),
            _candidate_claim(
                field_path="cover_letter.secondary_evidence",
                claim_text=secondary,
                evidence_atom_ids=["atom-image-quality-process"],
                claim_type=CandidateClaimType.COVER_LETTER,
                certainty=ClaimCertainty.OBSERVED,
            ),
            _candidate_claim(
                field_path="cover_letter.closing",
                claim_text=closing,
                evidence_atom_ids=["atom-target-role"],
                claim_type=CandidateClaimType.COVER_LETTER,
                certainty=ClaimCertainty.ASPIRATIONAL,
            ),
            *[
                _candidate_claim(
                    field_path=f"application_snippets.{index}.answer",
                    claim_text=snippet.answer,
                    evidence_atom_ids=snippet.evidence_atom_ids,
                    claim_type=CandidateClaimType.APPLICATION_ANSWER,
                    tools_claimed=snippet.tools_claimed,
                    outcome_claimed=snippet.outcome_claimed,
                    certainty=snippet.certainty,
                )
                for index, snippet in enumerate(snippets)
            ],
        ],
        strategy_notes=["Prioritized direct proof."],
        quality_review_notes=["Concise and evidence-backed."],
    )


def _claim(output: ApplicationWritingOutput, field_path: str) -> CandidateFacingClaim:
    return next(
        claim for claim in output.candidate_claims if claim.field_path == field_path
    )


def _rebuild_cover_full_text(output: ApplicationWritingOutput) -> None:
    cover = output.cover_letter
    cover.full_text = " ".join(
        (cover.opening, cover.primary_evidence, cover.secondary_evidence, cover.closing)
    )


def _supported_image_outcome(
    writing_input: ApplicationWritingInput,
) -> StructuredOutcome:
    atom = next(
        atom
        for atom in writing_input.evidence_ledger
        if atom.evidence_atom_id == "atom-image-review-consistency"
    )
    assert atom.supported_outcome is not None
    return atom.supported_outcome


def _set_resume_outcome(
    output: ApplicationWritingOutput,
    *,
    text: str,
    outcome: StructuredOutcome,
    certainty: ClaimCertainty = ClaimCertainty.OBSERVED,
    group_memory_id: str = IMAGE_MEMORY_ID,
    legacy_reference: str = IMAGE_QUALITY_REF,
) -> None:
    group = output.resume_bullet_groups[0]
    group.memory_id = group_memory_id
    group.heading = "Image Categorization and Data Quality Project"
    group.bullets[0].text = text
    group.bullets[0].evidence_reference_ids = [legacy_reference]
    claim = _claim(output, RESUME_PATH)
    claim.claim_text = text
    claim.evidence_atom_ids = ["atom-image-review-consistency"]
    claim.tools_claimed = []
    claim.outcome_claimed = outcome
    claim.certainty = certainty


def _assert_diagnostic(
    error: ApplicationWritingMalformedOutputError,
    *,
    code: ApplicationWritingValidationCode,
    section: str,
    field_path: str,
    phrase: str,
    evidence_atom_ids: list[str],
) -> None:
    diagnostic = error.validation_diagnostic
    assert diagnostic is not None
    assert diagnostic.validation_rule_code is code
    assert diagnostic.output_section == section
    assert diagnostic.field_path == field_path
    assert diagnostic.normalized_disputed_phrase == phrase
    assert diagnostic.referenced_evidence_ids == evidence_atom_ids
    assert diagnostic.surface_classification == "user-facing"


@pytest.mark.parametrize("question_count", [0, 1, 3])
def test_application_answers_follow_dynamic_question_count(
    question_count: int,
) -> None:
    writing_input = _writing_input()
    writing_input = writing_input.model_copy(
        update={
            "application_questions": writing_input.application_questions[
                :question_count
            ]
        }
    )
    output = _valid_output(writing_input)

    validate_application_writing_output_contract(writing_input, output)

    assert [item.question_id for item in output.application_snippets] == [
        item.question_id for item in writing_input.application_questions
    ]
    assert all(item.evidence_reference_ids for item in output.application_snippets)
    assert all(item.evidence_atom_ids for item in output.application_snippets)


def test_missing_required_application_answer_is_blocked() -> None:
    writing_input = _writing_input()
    output = _valid_output(writing_input)
    output.application_snippets.pop()

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    _assert_diagnostic(
        caught.value,
        code=ApplicationWritingValidationCode.MISSING_REQUIRED_APPLICATION_ANSWER,
        section="application-answers",
        field_path="application_snippets.quality-reliability",
        phrase="quality-reliability",
        evidence_atom_ids=[],
    )


def test_duplicate_application_answer_is_blocked() -> None:
    writing_input = _writing_input()
    output = _valid_output(writing_input)
    output.application_snippets[1] = output.application_snippets[1].model_copy(
        update={"question_id": "motivation"}
    )

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    _assert_diagnostic(
        caught.value,
        code=ApplicationWritingValidationCode.DUPLICATE_APPLICATION_ANSWER,
        section="application-answers",
        field_path="application_snippets.motivation",
        phrase="motivation",
        evidence_atom_ids=[],
    )


def test_unknown_application_question_id_is_blocked() -> None:
    writing_input = _writing_input()
    output = _valid_output(writing_input)
    output.application_snippets[0] = output.application_snippets[0].model_copy(
        update={"question_id": "provider-invented-question"}
    )

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    _assert_diagnostic(
        caught.value,
        code=ApplicationWritingValidationCode.UNKNOWN_APPLICATION_QUESTION_ID,
        section="application-answers",
        field_path="application_snippets.provider-invented-question",
        phrase="provider-invented-question",
        evidence_atom_ids=[],
    )


def test_empty_application_answer_is_blocked() -> None:
    writing_input = _writing_input()
    output = _valid_output(writing_input)
    answer = output.application_snippets[0]
    output.application_snippets[0] = answer.model_copy(update={"answer": "   "})

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    _assert_diagnostic(
        caught.value,
        code=ApplicationWritingValidationCode.EMPTY_APPLICATION_ANSWER,
        section="application-answers",
        field_path="application_snippets.motivation.answer",
        phrase="empty answer",
        evidence_atom_ids=answer.evidence_atom_ids,
    )


def test_application_answer_order_must_match_supplied_question_order() -> None:
    writing_input = _writing_input()
    output = _valid_output(writing_input)
    output.application_snippets = list(reversed(output.application_snippets))

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    _assert_diagnostic(
        caught.value,
        code=ApplicationWritingValidationCode.APPLICATION_ANSWER_ORDER_MISMATCH,
        section="application-answers",
        field_path="application_snippets",
        phrase="answer order mismatch",
        evidence_atom_ids=[],
    )


def test_optional_application_question_may_be_omitted() -> None:
    writing_input = _writing_input()
    optional_question = ApplicationQuestionInput(
        question_id="optional-additional-context",
        question_text="Is there any additional context you would like to share?",
        required=False,
        response_type="long-text",
    )
    writing_input = writing_input.model_copy(
        update={
            "application_questions": [
                writing_input.application_questions[0],
                optional_question,
            ]
        }
    )
    output = _valid_output(writing_input)

    validate_application_writing_output_contract(writing_input, output)

    assert [item.question_id for item in output.application_snippets] == ["motivation"]


def test_safe_outcome_paraphrase_is_allowed() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    expected = _supported_image_outcome(writing_input)
    paraphrase = expected.model_copy(
        update={
            "action": "strengthened",
            "object": "reviewed image collection consistency",
            "outcome": (
                "Strengthened consistency across reviews of the image collection."
            ),
        }
    )
    _set_resume_outcome(
        output,
        text="Strengthened consistency across reviews of the image collection.",
        outcome=paraphrase,
    )

    validate_application_writing_output_contract(writing_input, output)


def test_changed_outcome_object_is_blocked() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    changed = _supported_image_outcome(writing_input).model_copy(
        update={
            "object": "model accuracy",
            "outcome": "Improved model accuracy.",
        }
    )
    _set_resume_outcome(
        output,
        text="Improved model accuracy.",
        outcome=changed,
    )

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    _assert_diagnostic(
        caught.value,
        code=ApplicationWritingValidationCode.OUTCOME_OBJECT_MISMATCH,
        section="resume",
        field_path=RESUME_PATH,
        phrase="model accuracy",
        evidence_atom_ids=["atom-image-review-consistency"],
    )


def test_disputed_phrase_redacts_identifiers_and_secret_shaped_text() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    private_object = "model accuracy analyst@example.com sk-abcdefghijklmnop"
    changed = _supported_image_outcome(writing_input).model_copy(
        update={
            "object": private_object,
            "outcome": f"Improved {private_object}.",
        }
    )
    _set_resume_outcome(
        output,
        text=f"Improved {private_object}.",
        outcome=changed,
    )

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert "analyst@example.com" not in diagnostic.normalized_disputed_phrase
    assert "sk-abcdefghijklmnop" not in diagnostic.normalized_disputed_phrase
    assert "redacted" in diagnostic.normalized_disputed_phrase


def test_outcome_expansion_with_new_object_and_result_is_blocked() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    expected = _supported_image_outcome(writing_input)
    expanded = expected.model_copy(
        update={
            "object": f"{expected.object} and model accuracy",
            "outcome": f"{expected.outcome} and increased business impact",
        }
    )
    _set_resume_outcome(
        output,
        text=(
            "Improved consistency of the reviewed image collection and model "
            "accuracy, increasing business impact."
        ),
        outcome=expanded,
    )

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert (
        diagnostic.validation_rule_code
        is ApplicationWritingValidationCode.OUTCOME_OBJECT_MISMATCH
    )
    assert diagnostic.field_path == RESUME_PATH


def test_outcome_single_token_expansion_is_blocked() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    expected = _supported_image_outcome(writing_input)
    expanded = expected.model_copy(
        update={
            "object": f"{expected.object} accuracy",
            "outcome": f"{expected.outcome.rstrip('.')} accuracy.",
        }
    )
    _set_resume_outcome(
        output,
        text="Improved consistency of the reviewed image collection accuracy.",
        outcome=expanded,
    )

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert (
        diagnostic.validation_rule_code
        is ApplicationWritingValidationCode.OUTCOME_OBJECT_MISMATCH
    )
    assert diagnostic.field_path == RESUME_PATH


def test_changed_outcome_metric_is_blocked() -> None:
    writing_input = _writing_input()
    atom = next(
        atom
        for atom in writing_input.evidence_ledger
        if atom.evidence_atom_id == "atom-image-review-consistency"
    )
    assert atom.supported_outcome is not None
    atom.factual_statement = (
        "A fictional benchmark improved consistency of the reviewed image "
        "collection by 12%."
    )
    atom.supported_outcome = atom.supported_outcome.model_copy(
        update={
            "outcome": (
                "Improved consistency of the reviewed image collection by 12%."
            ),
            "metric": "12%",
        }
    )
    output = _valid_output()
    changed = atom.supported_outcome.model_copy(
        update={
            "outcome": (
                "Improved consistency of the reviewed image collection by 20%."
            ),
            "metric": "20%",
        }
    )
    _set_resume_outcome(
        output,
        text="Improved consistency of the reviewed image collection by 20%.",
        outcome=changed,
    )

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    _assert_diagnostic(
        caught.value,
        code=ApplicationWritingValidationCode.UNSUPPORTED_METRIC,
        section="resume",
        field_path=RESUME_PATH,
        phrase="20%",
        evidence_atom_ids=["atom-image-review-consistency"],
    )


def test_inflated_outcome_certainty_is_blocked() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    inflated = _supported_image_outcome(writing_input).model_copy(
        update={"certainty": ClaimCertainty.CAUSAL}
    )
    _set_resume_outcome(
        output,
        text="Improved consistency of the reviewed image collection.",
        outcome=inflated,
        certainty=ClaimCertainty.CAUSAL,
    )

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    _assert_diagnostic(
        caught.value,
        code=ApplicationWritingValidationCode.OUTCOME_CERTAINTY_INFLATION,
        section="resume",
        field_path=RESUME_PATH,
        phrase="causal",
        evidence_atom_ids=["atom-image-review-consistency"],
    )


def test_claim_certainty_cannot_be_laundered_through_an_unrelated_atom() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    outcome_atom = next(
        atom
        for atom in writing_input.evidence_ledger
        if atom.evidence_atom_id == "atom-image-review-consistency"
    )
    assert outcome_atom.supported_outcome is not None
    qualified_outcome = outcome_atom.supported_outcome.model_copy(
        update={"certainty": ClaimCertainty.QUALIFIED}
    )
    outcome_atom.supported_outcome = qualified_outcome
    outcome_atom.allowed_certainty = ClaimCertainty.QUALIFIED
    _set_resume_outcome(
        output,
        text="Improved consistency of the reviewed image collection.",
        outcome=qualified_outcome,
        certainty=ClaimCertainty.OBSERVED,
    )
    claim = _claim(output, RESUME_PATH)
    claim.evidence_atom_ids.append("atom-image-quality-process")

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert (
        diagnostic.validation_rule_code
        is ApplicationWritingValidationCode.OUTCOME_CERTAINTY_INFLATION
    )
    assert diagnostic.field_path == RESUME_PATH


def test_cross_project_outcome_leakage_is_blocked() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    outcome = _supported_image_outcome(writing_input)
    _set_resume_outcome(
        output,
        text="Improved consistency of the reviewed image collection.",
        outcome=outcome,
        group_memory_id=SCIENTIFIC_MEMORY_ID,
        legacy_reference=SCIENTIFIC_WORKFLOW_REF,
    )

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    _assert_diagnostic(
        caught.value,
        code=ApplicationWritingValidationCode.CROSS_MEMORY_CLAIM_LEAKAGE,
        section="resume",
        field_path=RESUME_PATH,
        phrase=SCIENTIFIC_MEMORY_ID,
        evidence_atom_ids=["atom-image-review-consistency"],
    )


def test_unsupported_tool_is_allowed_in_analysis_only_unsupported_requirements() -> (
    None
):
    writing_input = _writing_input()
    output = _valid_output()
    output.unsupported_requirements.append(
        UnsupportedRequirementOutput(
            requirement="Kubernetes",
            explanation=(
                "Kubernetes appears in the fictional target requirements, but no "
                "selected evidence atom supports claiming it."
            ),
        )
    )

    validate_application_writing_output_contract(writing_input, output)


def test_tool_in_exact_target_title_is_allowed_only_as_application_framing() -> None:
    writing_input = _writing_input()
    writing_input.target_role = "2026 AWS Cloud Intern"
    target_atom = next(
        atom
        for atom in writing_input.evidence_ledger
        if atom.evidence_atom_id == "atom-target-role"
    )
    target_atom.factual_statement = "The target is the 2026 AWS Cloud Intern role."
    output = _valid_output()
    opening = "I am applying for the 2026 AWS Cloud Intern role."
    output.cover_letter.opening = opening
    _claim(output, "cover_letter.opening").claim_text = opening
    _rebuild_cover_full_text(output)

    validate_application_writing_output_contract(writing_input, output)


def test_target_title_cannot_be_recast_as_candidate_experience() -> None:
    writing_input = _writing_input()
    writing_input.target_role = "2026 AWS Cloud Intern"
    target_atom = next(
        atom
        for atom in writing_input.evidence_ledger
        if atom.evidence_atom_id == "atom-target-role"
    )
    target_atom.factual_statement = "The target is the 2026 AWS Cloud Intern role."
    output = _valid_output()
    opening = "I worked as a 2026 AWS Cloud Intern."
    output.cover_letter.opening = opening
    opening_claim = _claim(output, "cover_letter.opening")
    opening_claim.claim_text = opening
    opening_claim.tools_claimed = ["AWS"]
    _rebuild_cover_full_text(output)

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    _assert_diagnostic(
        caught.value,
        code=ApplicationWritingValidationCode.UNSUPPORTED_CONCRETE_TOOL,
        section="cover-letter",
        field_path="cover_letter.opening",
        phrase="aws",
        evidence_atom_ids=["atom-target-role"],
    )


@pytest.mark.parametrize(
    ("section", "field_path"),
    [
        ("positioning", POSITIONING_PATH),
        ("resume", RESUME_PATH),
        ("cover-letter", COVER_PRIMARY_PATH),
        ("application-answer", SNIPPET_PROJECT_PATH),
    ],
)
def test_unsupported_tool_is_blocked_in_each_candidate_section(
    section: str,
    field_path: str,
) -> None:
    writing_input = _writing_input()
    output = _valid_output()
    claim = _claim(output, field_path)
    text = f"{claim.claim_text} I used Kubernetes."
    claim.claim_text = text
    claim.tools_claimed = [*claim.tools_claimed, "Kubernetes"]
    if field_path == POSITIONING_PATH:
        output.positioning_summary = text
    elif field_path == RESUME_PATH:
        output.resume_bullet_groups[0].bullets[0].text = text
    elif field_path == COVER_PRIMARY_PATH:
        output.cover_letter.primary_evidence = text
        _rebuild_cover_full_text(output)
    else:
        output.application_snippets[1].answer = text
        output.application_snippets[1].tools_claimed = claim.tools_claimed

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    _assert_diagnostic(
        caught.value,
        code=ApplicationWritingValidationCode.UNSUPPORTED_CONCRETE_TOOL,
        section=section,
        field_path=field_path,
        phrase="kubernetes",
        evidence_atom_ids=claim.evidence_atom_ids,
    )


def test_unsupported_deployment_claim_is_blocked() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    claim = _claim(output, RESUME_PATH)
    text = f"{claim.claim_text} Completed a production deployment."
    claim.claim_text = text
    claim.tools_claimed = [*claim.tools_claimed, "production deployment"]
    output.resume_bullet_groups[0].bullets[0].text = text

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    _assert_diagnostic(
        caught.value,
        code=ApplicationWritingValidationCode.UNSUPPORTED_DEPLOYMENT_CLAIM,
        section="resume",
        field_path=RESUME_PATH,
        phrase="production deployment",
        evidence_atom_ids=claim.evidence_atom_ids,
    )


def test_unrelated_general_claim_cannot_borrow_a_valid_evidence_atom() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    claim = _claim(output, RESUME_PATH)
    unrelated_claim = f"{claim.claim_text} I managed a cross-functional team."
    claim.claim_text = unrelated_claim
    output.resume_bullet_groups[0].bullets[0].text = unrelated_claim

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert diagnostic.field_path == RESUME_PATH


def test_material_same_sentence_expansion_cannot_hide_in_supported_text() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    claim = _claim(output, RESUME_PATH)
    expanded = (
        "Built a reproducible Python workflow that managed a cross-functional team."
    )
    claim.claim_text = expanded
    output.resume_bullet_groups[0].bullets[0].text = expanded

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert (
        diagnostic.validation_rule_code
        is ApplicationWritingValidationCode.UNSUPPORTED_FACTUAL_CLAIM
    )
    assert diagnostic.field_path == RESUME_PATH


def test_dynamic_concrete_tool_requirement_is_blocked_in_candidate_text() -> None:
    writing_input = _writing_input()
    writing_input.grouped_requirements.concrete_tools_requiring_direct_proof.append(
        "Java"
    )
    output = _valid_output()
    claim = _claim(output, RESUME_PATH)
    unsupported_claim = f"{claim.claim_text} I used Java."
    claim.claim_text = unsupported_claim
    output.resume_bullet_groups[0].bullets[0].text = unsupported_claim

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    _assert_diagnostic(
        caught.value,
        code=ApplicationWritingValidationCode.UNSUPPORTED_CONCRETE_TOOL,
        section="resume",
        field_path=RESUME_PATH,
        phrase="java",
        evidence_atom_ids=claim.evidence_atom_ids,
    )


def test_production_wording_requires_direct_deployment_proof() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    claim = _claim(output, RESUME_PATH)
    unsupported_claim = (
        f"{claim.claim_text} I operated production machine-learning systems."
    )
    claim.claim_text = unsupported_claim
    output.resume_bullet_groups[0].bullets[0].text = unsupported_claim

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert (
        diagnostic.validation_rule_code
        is ApplicationWritingValidationCode.UNSUPPORTED_DEPLOYMENT_CLAIM
    )
    assert diagnostic.field_path == RESUME_PATH


def test_unstructured_research_observation_requires_supported_outcome() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    claim = _claim(output, RESUME_PATH)
    unsupported_claim = f"{claim.claim_text} I observed higher model accuracy."
    claim.claim_text = unsupported_claim
    output.resume_bullet_groups[0].bullets[0].text = unsupported_claim

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    _assert_diagnostic(
        caught.value,
        code=ApplicationWritingValidationCode.UNSUPPORTED_OUTCOME,
        section="resume",
        field_path=RESUME_PATH,
        phrase="unstructured outcome",
        evidence_atom_ids=claim.evidence_atom_ids,
    )


def test_unknown_evidence_atom_reference_has_safe_diagnostic() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    claim = _claim(output, POSITIONING_PATH)
    claim.evidence_atom_ids = ["atom-unknown-provider-reference"]

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    _assert_diagnostic(
        caught.value,
        code=ApplicationWritingValidationCode.UNKNOWN_EVIDENCE_REFERENCE,
        section="positioning",
        field_path=POSITIONING_PATH,
        phrase="atom-unknown-provider-reference",
        evidence_atom_ids=["atom-unknown-provider-reference"],
    )
    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert diagnostic.expected_evidence_category == "immutable approved evidence atom"
    assert claim.claim_text not in str(caught.value)
    assert writing_input.job_description not in str(caught.value)


@pytest.mark.parametrize("atom_id", ["atom-target-role", "atom-scientific-framing"])
def test_context_or_framing_only_atom_is_rejected(atom_id: str) -> None:
    writing_input = _writing_input()
    output = _valid_output()
    claim = _claim(output, POSITIONING_PATH)
    claim.evidence_atom_ids = [atom_id]
    claim.tools_claimed = []

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    _assert_diagnostic(
        caught.value,
        code=ApplicationWritingValidationCode.UNKNOWN_EVIDENCE_REFERENCE,
        section="positioning",
        field_path=POSITIONING_PATH,
        phrase="context-only evidence",
        evidence_atom_ids=[atom_id],
    )
    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert diagnostic.expected_evidence_category == "direct approved evidence atom"


def test_optional_unsupported_warning_is_removed_and_recorded() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    claim = _claim(output, RESUME_PATH)
    supported_core = claim.claim_text
    text_with_warning = f"{supported_core} (Kubernetes is unsupported.)"
    claim.claim_text = text_with_warning
    claim.tools_claimed = [*claim.tools_claimed, "Kubernetes"]
    output.resume_bullet_groups[0].bullets[0].text = text_with_warning

    sanitized = sanitize_application_writing_output(writing_input, output)

    assert sanitized.resume_bullet_groups[0].bullets[0].text == supported_core
    sanitized_claim = _claim(sanitized, RESUME_PATH)
    assert sanitized_claim.claim_text == supported_core
    assert sanitized_claim.tools_claimed == ["Python"]
    assert output.resume_bullet_groups[0].bullets[0].text == text_with_warning
    assert claim.claim_text == text_with_warning
    assert len(sanitized.validation_metadata.repairs) == 1
    repair = sanitized.validation_metadata.repairs[0]
    assert repair.code == "REMOVE_OPTIONAL_UNSUPPORTED_WARNING"
    assert repair.output_section == "resume"
    assert repair.field_path == RESUME_PATH
    assert repair.normalized_disputed_phrase == "kubernetes"
    assert repair.referenced_evidence_ids == ["atom-scientific-python-workflow"]
    assert repair.action == "Removed a separable unsupported-warning sentence."


def test_material_unsupported_claim_is_not_auto_repaired() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    claim = _claim(output, RESUME_PATH)
    material_claim = (
        "Built a reproducible Python workflow and deployed a Kubernetes service "
        "to production."
    )
    claim.claim_text = material_claim
    claim.tools_claimed = ["Python", "Kubernetes", "production deployment"]
    output.resume_bullet_groups[0].bullets[0].text = material_claim

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        sanitize_application_writing_output(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert diagnostic.validation_rule_code in {
        ApplicationWritingValidationCode.UNSUPPORTED_CONCRETE_TOOL,
        ApplicationWritingValidationCode.UNSUPPORTED_DEPLOYMENT_CLAIM,
    }
    assert diagnostic.field_path == RESUME_PATH
    assert output.resume_bullet_groups[0].bullets[0].text == material_claim
    assert claim.claim_text == material_claim
    assert output.validation_metadata.repairs == []


@pytest.mark.parametrize(
    "unsupported_claim",
    [
        (
            "Built a reproducible Python workflow and managed a team, and I "
            "would welcome the opportunity."
        ),
        "I supervised interns and want to contribute these skills.",
    ],
)
def test_aspirational_tail_cannot_hide_an_unsupported_factual_claim(
    unsupported_claim: str,
) -> None:
    writing_input = _writing_input()
    output = _valid_output()
    claim = _claim(output, RESUME_PATH)
    claim.claim_text = unsupported_claim
    output.resume_bullet_groups[0].bullets[0].text = unsupported_claim

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert (
        diagnostic.validation_rule_code
        is ApplicationWritingValidationCode.UNSUPPORTED_FACTUAL_CLAIM
    )
    assert diagnostic.field_path == RESUME_PATH


@pytest.mark.parametrize(
    "unsupported_claim",
    [
        "I want to manage a team.",
        "Thank you for considering my application while I supervise interns.",
    ],
)
def test_whole_sentence_aspirational_framing_cannot_hide_a_material_claim(
    unsupported_claim: str,
) -> None:
    writing_input = _writing_input()
    output = _valid_output()
    output.cover_letter.opening = unsupported_claim
    claim = _claim(output, "cover_letter.opening")
    claim.claim_text = unsupported_claim
    _rebuild_cover_full_text(output)

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert (
        diagnostic.validation_rule_code
        is ApplicationWritingValidationCode.UNSUPPORTED_FACTUAL_CLAIM
    )
    assert diagnostic.field_path == "cover_letter.opening"


@pytest.mark.parametrize(
    "unsupported_suffix",
    [
        " and partnered with executives.",
        " with executive sponsorship.",
        " while supervising interns.",
    ],
)
def test_supported_text_cannot_carry_an_unrelated_factual_expansion(
    unsupported_suffix: str,
) -> None:
    writing_input = _writing_input()
    output = _valid_output()
    claim = _claim(output, RESUME_PATH)
    unsupported_claim = f"{claim.claim_text.rstrip('.')}{unsupported_suffix}"
    claim.claim_text = unsupported_claim
    output.resume_bullet_groups[0].bullets[0].text = unsupported_claim

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert (
        diagnostic.validation_rule_code
        is ApplicationWritingValidationCode.UNSUPPORTED_FACTUAL_CLAIM
    )
    assert diagnostic.field_path == RESUME_PATH


@pytest.mark.parametrize(
    "unsupported_tool",
    ["Snowflake", "Spark", "Databricks", "Airflow", "Terraform"],
)
def test_arbitrary_concrete_tool_is_blocked_when_metadata_omits_it(
    unsupported_tool: str,
) -> None:
    writing_input = _writing_input()
    output = _valid_output()
    claim = _claim(output, RESUME_PATH)
    unsupported_claim = f"{claim.claim_text.rstrip('.')} using {unsupported_tool}."
    claim.claim_text = unsupported_claim
    output.resume_bullet_groups[0].bullets[0].text = unsupported_claim

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert (
        diagnostic.validation_rule_code
        is ApplicationWritingValidationCode.UNSUPPORTED_CONCRETE_TOOL
    )
    assert diagnostic.field_path == RESUME_PATH
    assert diagnostic.normalized_disputed_phrase == unsupported_tool.casefold()


@pytest.mark.parametrize(
    "unsupported_outcome",
    [
        "and demonstrated measurable gains",
        "and revealed stronger results",
        "and yielded better outcomes",
    ],
)
def test_unstructured_outcome_synonym_requires_structured_support(
    unsupported_outcome: str,
) -> None:
    writing_input = _writing_input()
    output = _valid_output()
    claim = _claim(output, RESUME_PATH)
    unsupported_claim = f"{claim.claim_text.rstrip('.')} {unsupported_outcome}."
    claim.claim_text = unsupported_claim
    output.resume_bullet_groups[0].bullets[0].text = unsupported_claim

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    _assert_diagnostic(
        caught.value,
        code=ApplicationWritingValidationCode.UNSUPPORTED_OUTCOME,
        section="resume",
        field_path=RESUME_PATH,
        phrase="unstructured outcome",
        evidence_atom_ids=claim.evidence_atom_ids,
    )


def test_present_tense_target_team_support_is_not_application_framing() -> None:
    writing_input = _writing_input()
    writing_input.target_role = "AWS Cloud Intern"
    target_atom = next(
        atom
        for atom in writing_input.evidence_ledger
        if atom.evidence_atom_id == "atom-target-role"
    )
    target_atom.factual_statement = "The target is the AWS Cloud Intern role."
    output = _valid_output()
    opening = "I support the AWS Cloud Intern team."
    output.cover_letter.opening = opening
    opening_claim = _claim(output, "cover_letter.opening")
    opening_claim.claim_text = opening
    opening_claim.tools_claimed = []
    _rebuild_cover_full_text(output)

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    _assert_diagnostic(
        caught.value,
        code=ApplicationWritingValidationCode.UNSUPPORTED_CONCRETE_TOOL,
        section="cover-letter",
        field_path="cover_letter.opening",
        phrase="aws",
        evidence_atom_ids=["atom-target-role"],
    )


def test_modal_target_team_support_remains_safe_application_framing() -> None:
    writing_input = _writing_input()
    writing_input.target_role = "AWS Cloud Intern"
    target_atom = next(
        atom
        for atom in writing_input.evidence_ledger
        if atom.evidence_atom_id == "atom-target-role"
    )
    target_atom.factual_statement = "The target is the AWS Cloud Intern role."
    output = _valid_output()
    opening = "I would welcome the opportunity to support the AWS Cloud Intern team."
    output.cover_letter.opening = opening
    _claim(output, "cover_letter.opening").claim_text = opening
    _rebuild_cover_full_text(output)

    validate_application_writing_output_contract(writing_input, output)


def test_collective_actor_cannot_borrow_an_individual_evidence_atom() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    claim = _claim(output, RESUME_PATH)
    collective_claim = (
        "We built a reproducible Python workflow joining spectroscopy and imaging "
        "tables."
    )
    claim.claim_text = collective_claim
    output.resume_bullet_groups[0].bullets[0].text = collective_claim

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert (
        diagnostic.validation_rule_code
        is ApplicationWritingValidationCode.UNSUPPORTED_FACTUAL_CLAIM
    )
    assert diagnostic.field_path == RESUME_PATH


def test_untrusted_diagnostic_identifiers_are_redacted() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    malicious_field_path = "analyst@example.com"
    malicious_reference = "sk-abcdefghijklmnop"
    output.candidate_claims.append(
        _candidate_claim(
            field_path=malicious_field_path,
            claim_text="Untrusted metadata record.",
            evidence_atom_ids=[malicious_reference],
            claim_type=CandidateClaimType.POSITIONING,
            certainty=ClaimCertainty.OBSERVED,
        )
    )

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert malicious_field_path not in diagnostic.field_path
    assert malicious_reference not in diagnostic.referenced_evidence_ids
    assert "analyst@example.com" not in diagnostic.model_dump_json()
    assert "sk-abcdefghijklmnop" not in diagnostic.model_dump_json()


def test_evidence_reference_ownership_mismatch_is_analysis_only() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    output.evidence_references_used[0].memory_id = IMAGE_MEMORY_ID

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert diagnostic.field_path == "evidence_references_used"
    assert diagnostic.surface_classification == "analysis-only"


@pytest.mark.parametrize(
    "unsupported_suffix",
    [
        "and coordinated with directors",
        "and mentored analysts",
        "and trained staff",
        "and presented findings to the board",
        "and negotiated vendor contracts",
        "and owned strategy",
        "and advised senior leaders",
        "and served as project lead",
        "and authored legal briefs",
    ],
)
def test_arbitrary_action_tail_cannot_borrow_a_supported_clause(
    unsupported_suffix: str,
) -> None:
    writing_input = _writing_input()
    output = _valid_output()
    claim = _claim(output, RESUME_PATH)
    unsupported_claim = f"{claim.claim_text.rstrip('.')} {unsupported_suffix}."
    claim.claim_text = unsupported_claim
    output.resume_bullet_groups[0].bullets[0].text = unsupported_claim

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert (
        diagnostic.validation_rule_code
        is ApplicationWritingValidationCode.UNSUPPORTED_FACTUAL_CLAIM
    )
    assert diagnostic.field_path == RESUME_PATH


@pytest.mark.parametrize(
    ("unsupported_suffix", "expected_tool"),
    [
        ("using dagster", "dagster"),
        ("using dbt", "dbt"),
        ("built with Dagster", "dagster"),
        ("on Dagster pipelines", "dagster"),
        ("and would bring Dagster expertise", "dagster"),
        ("on dagster pipelines", "dagster"),
        ("powered by Dagster", "dagster"),
        ("implemented in dagster", "dagster"),
        ("through Dagster", "dagster"),
        ("Dagster pipelines", "dagster"),
        ("built atop Dagster", "dagster"),
        ("ran Dagster", "dagster"),
        ("orchestrated with dagster", "dagster"),
        ("developed on dagster", "dagster"),
        ("integrated Dagster", "dagster"),
        ("Dagster-orchestrated workflows", "dagster"),
    ],
)
def test_tool_syntax_is_checked_when_metadata_omits_an_unknown_tool(
    unsupported_suffix: str,
    expected_tool: str,
) -> None:
    writing_input = _writing_input()
    output = _valid_output()
    claim = _claim(output, RESUME_PATH)
    unsupported_claim = f"{claim.claim_text.rstrip('.')} {unsupported_suffix}."
    claim.claim_text = unsupported_claim
    output.resume_bullet_groups[0].bullets[0].text = unsupported_claim

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert (
        diagnostic.validation_rule_code
        is ApplicationWritingValidationCode.UNSUPPORTED_CONCRETE_TOOL
    )
    assert diagnostic.normalized_disputed_phrase == expected_tool


@pytest.mark.parametrize(
    "unsupported_outcome",
    [
        "produced results",
        "delivered results",
        "generated meaningful value",
        "revealed benefits",
        "yielded value",
        "met goals",
        "was successful",
    ],
)
def test_additional_result_phrasing_requires_a_structured_outcome(
    unsupported_outcome: str,
) -> None:
    writing_input = _writing_input()
    output = _valid_output()
    claim = _claim(output, RESUME_PATH)
    unsupported_claim = f"{claim.claim_text.rstrip('.')} and {unsupported_outcome}."
    claim.claim_text = unsupported_claim
    output.resume_bullet_groups[0].bullets[0].text = unsupported_claim

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert (
        diagnostic.validation_rule_code
        is ApplicationWritingValidationCode.UNSUPPORTED_OUTCOME
    )


@pytest.mark.parametrize(
    "collective_claim",
    [
        (
            "Together, I built a reproducible Python workflow joining spectroscopy "
            "and imaging tables."
        ),
        (
            "The lab built a reproducible Python workflow joining spectroscopy and "
            "imaging tables."
        ),
        (
            "Collectively, I built a reproducible Python workflow joining "
            "spectroscopy and imaging tables."
        ),
        (
            "Jointly, I built a reproducible Python workflow joining spectroscopy "
            "and imaging tables."
        ),
        (
            "Alongside colleagues, I built a reproducible Python workflow joining "
            "spectroscopy and imaging tables."
        ),
        (
            "With my colleagues, I built a reproducible Python workflow joining "
            "spectroscopy and imaging tables."
        ),
        (
            "Researchers built a reproducible Python workflow joining spectroscopy "
            "and imaging tables."
        ),
        (
            "The research group built a reproducible Python workflow joining "
            "spectroscopy and imaging tables."
        ),
    ],
)
def test_collective_actor_variants_require_collective_evidence(
    collective_claim: str,
) -> None:
    writing_input = _writing_input()
    output = _valid_output()
    claim = _claim(output, RESUME_PATH)
    claim.claim_text = collective_claim
    output.resume_bullet_groups[0].bullets[0].text = collective_claim

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert (
        diagnostic.validation_rule_code
        is ApplicationWritingValidationCode.UNSUPPORTED_FACTUAL_CLAIM
    )


@pytest.mark.parametrize(
    "unsupported_claim",
    [
        "The current record is sparse, but I authored legal briefs.",
        "The current record is sparse because I authored legal briefs.",
        (
            "I would welcome the opportunity to contribute after I authored legal "
            "briefs."
        ),
        (
            "I would welcome the opportunity to contribute because I authored legal "
            "briefs."
        ),
        ("That combination would let me contribute after I authored legal briefs."),
        ("That combination would let me contribute since I authored legal briefs."),
        (
            "Thank you for considering my application given that I authored legal "
            "briefs."
        ),
        "I want to contribute as I presented results.",
        "I hope to contribute as I analyzed results.",
        "I am drawn to this role as I reviewed results.",
        "Thank you for considering how I documented results.",
        "That combination would let me contribute as I presented results.",
        "The current record is sparse as I presented results.",
        ("I would welcome the opportunity to discuss how I reviewed results."),
        "I want to contribute as my work presented results.",
        "I hope to contribute as the project analyzed results.",
        "Thank you for considering how my analysis documented results.",
        "The current record is sparse as this research presented results.",
    ],
)
def test_safe_prefix_cannot_exempt_a_trailing_past_fact(
    unsupported_claim: str,
) -> None:
    writing_input = _writing_input()
    output = _valid_output()
    output.cover_letter.opening = unsupported_claim
    claim = _claim(output, "cover_letter.opening")
    claim.claim_text = unsupported_claim
    _rebuild_cover_full_text(output)

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert (
        diagnostic.validation_rule_code
        is ApplicationWritingValidationCode.UNSUPPORTED_FACTUAL_CLAIM
    )


def test_jwt_shaped_untrusted_diagnostic_reference_is_redacted() -> None:
    writing_input = _writing_input()
    output = _valid_output()
    jwt_like = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJwcml2YXRlIn0.signaturepayload"
    output.candidate_claims.append(
        _candidate_claim(
            field_path="untrusted.provider.path",
            claim_text="Untrusted metadata record.",
            evidence_atom_ids=[jwt_like],
            claim_type=CandidateClaimType.POSITIONING,
            certainty=ClaimCertainty.OBSERVED,
        )
    )

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert jwt_like not in diagnostic.model_dump_json()
    assert diagnostic.referenced_evidence_ids == ["redacted"]


@pytest.mark.parametrize(
    "incidental_group_text",
    [
        "The comparison group was documented.",
        "Used collaborative filtering.",
        "Analyzed partner survey data.",
        "Modeled stakeholder preferences.",
    ],
)
def test_incidental_group_noun_does_not_prove_a_collective_actor(
    incidental_group_text: str,
) -> None:
    writing_input = _writing_input()
    atom = next(
        item
        for item in writing_input.evidence_ledger
        if item.evidence_atom_id == "atom-scientific-python-workflow"
    )
    atom.factual_statement = f"{atom.factual_statement} {incidental_group_text}"
    output = _valid_output()
    claim = _claim(output, RESUME_PATH)
    collective_claim = (
        "We built a reproducible Python workflow joining spectroscopy and imaging "
        "tables."
    )
    claim.claim_text = collective_claim
    output.resume_bullet_groups[0].bullets[0].text = collective_claim

    with pytest.raises(ApplicationWritingMalformedOutputError) as caught:
        validate_application_writing_output_contract(writing_input, output)

    diagnostic = caught.value.validation_diagnostic
    assert diagnostic is not None
    assert (
        diagnostic.validation_rule_code
        is ApplicationWritingValidationCode.UNSUPPORTED_FACTUAL_CLAIM
    )
