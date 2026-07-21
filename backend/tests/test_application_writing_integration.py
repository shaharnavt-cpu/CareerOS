"""Package-level integration coverage for Sprint 14.1 application writing."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator

import pytest

from app.core.config import Settings
from app.db.session import SessionLocal
from app.schemas.application_packages import ApplicationPackageCreateRequest
from app.schemas.proof_artifacts import (
    ProofArtifactCreateRequest,
    ProofArtifactStatus,
    ProofArtifactUpdateRequest,
)
from app.services.application_packages import (
    ApplicationPackageService,
    ApplicationPackageValidationError,
)
from app.services.application_writing_provider import (
    ApplicationQuestionInput,
    ApplicationSnippetOutput,
    ApplicationWriterDataPolicy,
    ApplicationWritingInput,
    ApplicationWritingOutput,
    ApplicationWritingProviderMetadata,
    ApplicationWritingRemoteProviderError,
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
    UnsupportedRequirementOutput,
    validate_application_writing_data_policy,
)
from app.services.proof_artifacts import ProofArtifactService
from tests.test_application_packages import (
    RichPackageFixture,
    _cleanup_package_user,
    _require_postgres,
)
from tests.test_career_memory_compiler import _seed_compiler_memories


@pytest.fixture
def writing_integration_fixture() -> Iterator[RichPackageFixture]:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_compiler_memories(user_id)
    try:
        yield RichPackageFixture(user_id=user_id, seeded=seeded)
    finally:
        _cleanup_package_user(user_id)


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "application_writer_provider": "local-deterministic",
        "application_writer_data_policy": "private",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _application_questions() -> list[ApplicationQuestionInput]:
    return [
        ApplicationQuestionInput(
            question_id="motivation",
            question_text="Why are you interested in this Data Science internship?",
            required=True,
        ),
        ApplicationQuestionInput(
            question_id="complex-data-project",
            question_text="Describe a project where you analyzed complex data.",
            required=True,
        ),
        ApplicationQuestionInput(
            question_id="quality-reliability",
            question_text=(
                "Describe how you ensured the quality or reliability of your work."
            ),
            required=True,
        ),
    ]


def _provider_output(
    writing_input: ApplicationWritingInput,
) -> ApplicationWritingOutput:
    primary = writing_input.selected_memories[0]
    secondary = (
        writing_input.selected_memories[1]
        if len(writing_input.selected_memories) > 1
        else primary
    )
    primary_reference = primary.evidence_reference_ids[0]
    secondary_reference = secondary.evidence_reference_ids[0]
    primary_atom = next(
        atom
        for atom in writing_input.evidence_ledger
        if atom.canonical_memory_id == primary.memory_id
        and primary_reference in atom.evidence_reference_ids
        and atom.supported_outcome is None
        and atom.approved_claim_id.startswith(("claim-approved-", "claim-component-"))
    )
    secondary_atom = next(
        atom
        for atom in writing_input.evidence_ledger
        if atom.canonical_memory_id == secondary.memory_id
        and secondary_reference in atom.evidence_reference_ids
        and atom.supported_outcome is None
        and atom.approved_claim_id.startswith(("claim-approved-", "claim-component-"))
    )
    target_atom = next(
        atom
        for atom in writing_input.evidence_ledger
        if atom.support_type.value == "target-context"
    )
    primary_claim = primary_atom.factual_statement
    secondary_claim = secondary_atom.factual_statement
    expected_question_ids = [
        "motivation",
        "complex-data-project",
        "quality-reliability",
    ]
    assert [
        question.question_id for question in writing_input.application_questions
    ] == expected_question_ids
    snippet_sources = [
        (
            writing_input.application_questions[0],
            primary_claim,
            primary_reference,
            primary_atom,
        ),
        (
            writing_input.application_questions[1],
            primary_claim,
            primary_reference,
            primary_atom,
        ),
        (
            writing_input.application_questions[2],
            secondary_claim,
            secondary_reference,
            secondary_atom,
        ),
    ]
    used_pairs = {
        (primary_reference, primary.memory_id),
        (secondary_reference, secondary.memory_id),
    }
    output = ApplicationWritingOutput(
        job_understanding=JobUnderstandingOutput(
            role_family="Data science",
            seniority="Intern",
            central_objective="Turn complex data into defensible findings.",
            core_responsibilities=writing_input.central_responsibilities,
            must_have_requirements=writing_input.grouped_requirements.must_have,
            preferred_requirements=writing_input.grouped_requirements.preferred,
            technical_expectations=writing_input.grouped_requirements.technical,
            communication_expectations=(
                writing_input.grouped_requirements.communication
            ),
            concrete_tools_requiring_direct_proof=(
                writing_input.grouped_requirements.concrete_tools_requiring_direct_proof
            ),
            broad_semantic_concepts=(
                writing_input.grouped_requirements.broad_semantic_concepts
            ),
        ),
        requirement_coverage=[
            RequirementCoverageItem(
                requirement="SQL",
                level=RequirementCoverageLevel.STRONGLY_SUPPORTED,
                explanation="Deliberately incorrect provider classification.",
                evidence_reference_ids=[primary_reference],
            )
        ],
        claim_plan=ClaimPlanOutput(
            primary_positioning=primary_claim,
            primary_proof_memory_id=primary.memory_id,
            secondary_proof_memory_ids=(
                [secondary.memory_id]
                if secondary.memory_id != primary.memory_id
                else []
            ),
            supported_requirements=["SQL"],
            unsupported_requirements=[],
            claims_not_to_make=writing_input.prohibited_claims,
            missing_evidence=[
                warning.explanation for warning in writing_input.missing_proof_warnings
            ],
            resume_strategy="Lead with the strongest analytical project.",
            cover_letter_strategy="Connect careful analysis to the target role.",
            snippet_strategy="Answer directly with one supported example.",
            tone="Direct and professional",
        ),
        unsupported_requirements=[
            UnsupportedRequirementOutput(
                requirement=warning.requirement,
                explanation=warning.explanation,
            )
            for warning in writing_input.missing_proof_warnings
            if warning.blocking_if_claimed
        ],
        positioning_summary=primary_claim,
        resume_bullet_groups=[
            ResumeBulletGroupOutput(
                memory_id=primary.memory_id,
                heading="Projects",
                bullets=[
                    ResumeBulletOutput(
                        text=primary_claim,
                        evidence_reference_ids=[primary_reference],
                    )
                ],
            )
        ],
        cover_letter=CoverLetterSectionsOutput(
            opening=f"I am applying for the {writing_input.target_role} role.",
            primary_evidence=primary_claim,
            secondary_evidence=secondary_claim,
            closing="I would welcome the opportunity to contribute this approach.",
            full_text=" ".join(
                [
                    f"I am applying for the {writing_input.target_role} role.",
                    primary_claim,
                    secondary_claim,
                    "I would welcome the opportunity to contribute this approach.",
                ]
            ),
            evidence_reference_ids=[primary_reference, secondary_reference],
        ),
        application_snippets=[
            ApplicationSnippetOutput(
                question_id=question.question_id,
                answer=answer,
                evidence_reference_ids=[reference],
                evidence_atom_ids=[atom.evidence_atom_id],
                tools_claimed=[
                    tool
                    for tool in atom.supported_tools
                    if tool.casefold() in answer.casefold()
                ],
                outcome_claimed=atom.supported_outcome,
                certainty=atom.allowed_certainty,
            )
            for question, answer, reference, atom in snippet_sources
        ],
        evidence_references_used=[
            EvidenceReferenceUsed(
                evidence_reference_id=reference,
                memory_id=memory_id,
                usage="Supports a generated application surface.",
            )
            for reference, memory_id in sorted(used_pairs)
        ],
        strategy_notes=["Used the highest-ranked selected proof."],
        quality_review_notes=["Concise and evidence-linked."],
        provider_metadata=ApplicationWritingProviderMetadata(
            provider="openai",
            model="gpt-5.6-terra",
            request_id="resp_mock_integration",
            input_tokens=420,
            cached_input_tokens=40,
            output_tokens=760,
            latency_ms=1250,
        ),
    )
    primary_atoms = [primary_atom.evidence_atom_id]
    secondary_atoms = [secondary_atom.evidence_atom_id]
    target_atoms = [target_atom.evidence_atom_id]
    claims = [
        CandidateFacingClaim(
            field_path="positioning_summary",
            claim_text=output.positioning_summary,
            evidence_atom_ids=primary_atoms,
            claim_type=CandidateClaimType.POSITIONING,
            tools_claimed=[
                tool
                for tool in primary_atom.supported_tools
                if tool.casefold() in primary_claim.casefold()
            ],
            certainty=primary_atom.allowed_certainty,
        ),
        CandidateFacingClaim(
            field_path="resume_bullet_groups.0.bullets.0.text",
            claim_text=output.resume_bullet_groups[0].bullets[0].text,
            evidence_atom_ids=primary_atoms,
            claim_type=CandidateClaimType.RESUME_BULLET,
            tools_claimed=[
                tool
                for tool in primary_atom.supported_tools
                if tool.casefold() in primary_claim.casefold()
            ],
            certainty=primary_atom.allowed_certainty,
        ),
        *[
            CandidateFacingClaim(
                field_path=f"cover_letter.{field}",
                claim_text=getattr(output.cover_letter, field),
                evidence_atom_ids=(
                    target_atoms
                    if field in {"opening", "closing"}
                    else primary_atoms
                    if field == "primary_evidence"
                    else secondary_atoms
                ),
                claim_type=CandidateClaimType.COVER_LETTER,
                tools_claimed=(
                    [
                        tool
                        for tool in primary_atom.supported_tools
                        if tool.casefold()
                        in getattr(output.cover_letter, field).casefold()
                    ]
                    if field == "primary_evidence"
                    else [
                        tool
                        for tool in secondary_atom.supported_tools
                        if tool.casefold()
                        in getattr(output.cover_letter, field).casefold()
                    ]
                ),
                certainty=(
                    ClaimCertainty.ASPIRATIONAL
                    if field in {"opening", "closing"}
                    else (
                        primary_atom.allowed_certainty
                        if field == "primary_evidence"
                        else secondary_atom.allowed_certainty
                    )
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
                evidence_atom_ids=snippet.evidence_atom_ids,
                claim_type=CandidateClaimType.APPLICATION_ANSWER,
                tools_claimed=snippet.tools_claimed,
                outcome_claimed=snippet.outcome_claimed,
                certainty=snippet.certainty,
            )
            for index, snippet in enumerate(output.application_snippets)
        ],
    ]
    return output.model_copy(update={"candidate_claims": claims})


class _MockProvider:
    name = "mock-openai"

    def __init__(
        self,
        mutate: Callable[
            [ApplicationWritingInput, ApplicationWritingOutput],
            ApplicationWritingOutput,
        ]
        | None = None,
    ) -> None:
        self.calls: list[ApplicationWritingInput] = []
        self.mutate = mutate

    def generate_application_draft(
        self, writing_input: ApplicationWritingInput
    ) -> ApplicationWritingOutput:
        self.calls.append(writing_input)
        output = _provider_output(writing_input)
        return self.mutate(writing_input, output) if self.mutate else output


class _FailingProvider:
    name = "mock-openai"

    def generate_application_draft(
        self, writing_input: ApplicationWritingInput
    ) -> ApplicationWritingOutput:
        raise ApplicationWritingRemoteProviderError(
            "provider-error",
            "OpenAI could not complete the application-writing request.",
        )


class _DemoPolicyProvider(_MockProvider):
    def __init__(self) -> None:
        super().__init__()
        self.remote_calls = 0

    def generate_application_draft(
        self, writing_input: ApplicationWritingInput
    ) -> ApplicationWritingOutput:
        validate_application_writing_data_policy(
            writing_input, ApplicationWriterDataPolicy.DEMO_SHARED
        )
        self.remote_calls += 1
        return super().generate_application_draft(writing_input)


def _create_package(
    service: ApplicationPackageService,
    fixture: RichPackageFixture,
    *,
    target_description: str,
    required_skills: list[str] | None = None,
) -> uuid.UUID:
    with SessionLocal() as session:
        package = service.create(
            session,
            ApplicationPackageCreateRequest(
                role_title="Data Science Intern",
                company="Fictional Analytics Lab",
                target_description=target_description,
                required_skills=required_skills or [],
                application_questions=[
                    question.model_dump(mode="json")
                    for question in _application_questions()
                ],
                selected_memory_ids=[
                    fixture.seeded.gas_memory_id,
                    fixture.seeded.unicorn_memory_id,
                ],
            ),
        )
        return package.package_id


def test_mock_provider_metadata_and_server_semantic_coverage_are_persisted(
    writing_integration_fixture: RichPackageFixture,
) -> None:
    fixture = writing_integration_fixture
    provider = _MockProvider()
    service = ApplicationPackageService(
        user_id=fixture.user_id,
        settings=_settings(),
        writing_provider=provider,
    )
    package_id = _create_package(
        service,
        fixture,
        target_description=(
            "Analyze data, build models, maintain data quality, report findings, "
            "and communicate with partners. SQL, Tableau, and Power BI are required."
        ),
        required_skills=["SQL", "Tableau", "Power BI"],
    )

    with SessionLocal() as session:
        generated = service.generate(session, package_id)

    assert len(provider.calls) == 1
    assert len(provider.calls[0].selected_memories) == 2
    assert provider.calls[0].application_questions == _application_questions()
    assert generated.latest_version is not None
    version = generated.latest_version
    assert version.provider_metadata.provider == "openai"
    assert version.provider_metadata.model == "gpt-5.6-terra"
    assert version.provider_metadata.input_tokens == 420
    assert version.validation_summary.status == "PASS"
    strong = {
        item.requirement for item in version.requirement_coverage.strongly_supported
    }
    unsupported = {
        item.requirement for item in version.requirement_coverage.unsupported
    }
    assert {
        "data analysis",
        "modeling",
        "data quality",
        "technical communication",
    } <= strong
    assert {"SQL", "Tableau", "Power BI"} <= unsupported
    assert "SQL" not in version.outputs.positioning_summary.recommended_emphasis
    assert generated.evidence_groups
    assert len({item.memory_id for item in generated.evidence_groups}) == len(
        generated.evidence_groups
    )
    assert all(
        len(values) == len(set(values))
        for group in generated.evidence_groups
        for values in (
            group.direct_proof,
            group.approved_enrichment,
            group.supported_framing,
            group.strategy_signals,
            group.target_relevance,
        )
    )
    assert generated.warning_groups.unsupported
    assert version.quality_review.primary_issue


def test_provider_failure_preserves_the_existing_immutable_version(
    writing_integration_fixture: RichPackageFixture,
) -> None:
    fixture = writing_integration_fixture
    local_service = ApplicationPackageService(
        user_id=fixture.user_id,
        settings=_settings(),
    )
    package_id = _create_package(
        local_service,
        fixture,
        target_description="Analyze scientific data and communicate findings.",
    )
    with SessionLocal() as session:
        baseline = local_service.generate(session, package_id)
    assert baseline.latest_version is not None
    baseline_snapshot = baseline.latest_version.model_dump(mode="json")

    failing_service = ApplicationPackageService(
        user_id=fixture.user_id,
        settings=_settings(),
        writing_provider=_FailingProvider(),
    )
    with SessionLocal() as session:
        with pytest.raises(ApplicationPackageValidationError):
            failing_service.generate(session, package_id)
        preserved = failing_service.get(session, package_id)

    assert preserved.version_count == 1
    assert preserved.latest_version is not None
    assert preserved.latest_version.id == baseline.latest_version.id
    assert preserved.latest_version.model_dump(mode="json") == baseline_snapshot


def test_failed_missing_answer_repair_preserves_the_existing_immutable_version(
    writing_integration_fixture: RichPackageFixture,
) -> None:
    fixture = writing_integration_fixture
    local_service = ApplicationPackageService(
        user_id=fixture.user_id,
        settings=_settings(),
    )
    package_id = _create_package(
        local_service,
        fixture,
        target_description="Analyze scientific data and communicate findings.",
    )
    with SessionLocal() as session:
        baseline = local_service.generate(session, package_id)
    assert baseline.latest_version is not None
    baseline_snapshot = baseline.latest_version.model_dump(mode="json")

    def omit_required_answer(
        writing_input: ApplicationWritingInput,
        output: ApplicationWritingOutput,
    ) -> ApplicationWritingOutput:
        del writing_input
        retained_snippets = output.application_snippets[:-1]
        retained_claims = [
            claim
            for claim in output.candidate_claims
            if claim.field_path != "application_snippets.2.answer"
        ]
        return output.model_copy(
            update={
                "application_snippets": retained_snippets,
                "candidate_claims": retained_claims,
            }
        )

    failed_repair_service = ApplicationPackageService(
        user_id=fixture.user_id,
        settings=_settings(),
        writing_provider=_MockProvider(omit_required_answer),
    )
    with SessionLocal() as session:
        with pytest.raises(ApplicationPackageValidationError):
            failed_repair_service.regenerate(session, package_id)
        preserved = failed_repair_service.get(session, package_id)

    assert preserved.version_count == 1
    assert preserved.latest_version is not None
    assert preserved.latest_version.model_dump(mode="json") == baseline_snapshot


def test_semantic_validation_failure_preserves_the_existing_immutable_version(
    writing_integration_fixture: RichPackageFixture,
) -> None:
    fixture = writing_integration_fixture
    local_service = ApplicationPackageService(
        user_id=fixture.user_id,
        settings=_settings(),
    )
    package_id = _create_package(
        local_service,
        fixture,
        target_description="Analyze scientific data and communicate findings.",
    )
    with SessionLocal() as session:
        baseline = local_service.generate(session, package_id)
    assert baseline.latest_version is not None
    baseline_snapshot = baseline.latest_version.model_dump(mode="json")

    def invent_tool(
        writing_input: ApplicationWritingInput,
        output: ApplicationWritingOutput,
    ) -> ApplicationWritingOutput:
        bullet = output.resume_bullet_groups[0].bullets[0]
        material_claim = f"{bullet.text} Deployed a Kubernetes service."
        bullet.text = material_claim
        claim = next(
            item
            for item in output.candidate_claims
            if item.field_path == "resume_bullet_groups.0.bullets.0.text"
        )
        claim.claim_text = material_claim
        claim.tools_claimed = [
            *claim.tools_claimed,
            "Kubernetes",
            "production deployment",
        ]
        return output

    provider_service = ApplicationPackageService(
        user_id=fixture.user_id,
        settings=_settings(),
        writing_provider=_MockProvider(invent_tool),
    )
    with SessionLocal() as session:
        with pytest.raises(ApplicationPackageValidationError):
            provider_service.regenerate(session, package_id)
        preserved = provider_service.get(session, package_id)

    assert preserved.version_count == 1
    assert preserved.latest_version is not None
    assert preserved.latest_version.model_dump(mode="json") == baseline_snapshot


def test_safe_sanitizer_repair_metadata_is_persisted_round_trip(
    writing_integration_fixture: RichPackageFixture,
) -> None:
    fixture = writing_integration_fixture

    def add_optional_warning(
        writing_input: ApplicationWritingInput,
        output: ApplicationWritingOutput,
    ) -> ApplicationWritingOutput:
        bullet = output.resume_bullet_groups[0].bullets[0]
        supported_core = bullet.text
        text_with_warning = f"{supported_core} (Kubernetes is unsupported.)"
        bullet.text = text_with_warning
        claim = next(
            item
            for item in output.candidate_claims
            if item.field_path == "resume_bullet_groups.0.bullets.0.text"
        )
        claim.claim_text = text_with_warning
        claim.tools_claimed = [*claim.tools_claimed, "Kubernetes"]
        return output

    provider = _MockProvider(add_optional_warning)
    service = ApplicationPackageService(
        user_id=fixture.user_id,
        settings=_settings(),
        writing_provider=provider,
    )
    package_id = _create_package(
        service,
        fixture,
        target_description="Analyze scientific data and communicate findings.",
    )

    with SessionLocal() as session:
        generated = service.generate(session, package_id)

    assert generated.latest_version is not None
    version = generated.latest_version
    rendered = " ".join(
        bullet.bullet_text
        for group in version.outputs.resume_bullets
        for bullet in group.bullets
    )
    assert "Kubernetes" not in rendered
    assert version.validation_summary.unsupported_claims_removed == 1
    assert version.validation_summary.blocking_issue_count == 0
    assert len(version.validation_summary.repairs) == 1
    repair = version.validation_summary.repairs[0]
    assert repair.code == "REMOVE_OPTIONAL_UNSUPPORTED_WARNING"
    assert repair.output_section == "resume"
    assert repair.field_path == "resume_bullet_groups.0.bullets.0.text"
    assert repair.normalized_disputed_phrase == "kubernetes"
    persisted_resume_claim = next(
        item for item in version.claim_ledger if item.claim_id == "resume-1-1"
    )
    assert "Kubernetes" not in persisted_resume_claim.text
    assert "Kubernetes" not in persisted_resume_claim.tools_claimed


def test_unresolved_provider_outcome_and_strategy_signal_create_no_version(
    writing_integration_fixture: RichPackageFixture,
) -> None:
    fixture = writing_integration_fixture

    def invent_outcome(
        writing_input: ApplicationWritingInput,
        output: ApplicationWritingOutput,
    ) -> ApplicationWritingOutput:
        snippets = list(output.application_snippets)
        snippets[0] = snippets[0].model_copy(
            update={"answer": "I earned an interview invitation through this work."}
        )
        return output.model_copy(update={"application_snippets": snippets})

    provider = _MockProvider(invent_outcome)
    service = ApplicationPackageService(
        user_id=fixture.user_id,
        settings=_settings(),
        writing_provider=provider,
    )
    package_id = _create_package(
        service,
        fixture,
        target_description="Analyze scientific data and communicate findings.",
    )

    with SessionLocal() as session:
        with pytest.raises(ApplicationPackageValidationError):
            service.generate(session, package_id)
        preserved = service.get(session, package_id)

    assert provider.calls
    assert provider.calls[0].outcome_signals
    assert preserved.version_count == 0


def test_demo_shared_policy_rejects_personal_package_before_remote_work(
    writing_integration_fixture: RichPackageFixture,
) -> None:
    fixture = writing_integration_fixture
    provider = _DemoPolicyProvider()
    service = ApplicationPackageService(
        user_id=fixture.user_id,
        settings=_settings(application_writer_data_policy="demo-shared"),
        writing_provider=provider,
    )
    package_id = _create_package(
        service,
        fixture,
        target_description="Analyze scientific data and communicate findings.",
    )

    with SessionLocal() as session:
        with pytest.raises(ApplicationPackageValidationError):
            service.generate(session, package_id)
        preserved = service.get(session, package_id)

    assert provider.remote_calls == 0
    assert preserved.version_count == 0


def test_recommendations_default_to_two_to_four_and_description_only_tools_warn(
    writing_integration_fixture: RichPackageFixture,
) -> None:
    fixture = writing_integration_fixture
    service = ApplicationPackageService(
        user_id=fixture.user_id,
        settings=_settings(),
    )
    with SessionLocal() as session:
        options = service.list_eligible_memories(
            session, "Data Science Intern analyzing data quality and reporting"
        )
        ai_options = service.list_eligible_memories(
            session,
            "AI data-quality role with image labeling and human-in-the-loop review",
        )
    recommended = [item for item in options if item.recommended]
    assert 2 <= len(recommended) <= 4
    assert [item.recommendation_rank for item in recommended] == list(
        range(1, len(recommended) + 1)
    )
    assert ai_options[0].id == fixture.seeded.unicorn_memory_id
    assert 2 <= len([item for item in ai_options if item.recommended]) <= 4

    package_id = _create_package(
        service,
        fixture,
        target_description=(
            "Analyze datasets, report findings, use cloud infrastructure, and deploy "
            "reliable services."
        ),
    )
    with SessionLocal() as session:
        generated = service.generate(session, package_id)

    assert generated.latest_version is not None
    unsupported = {
        item.requirement
        for item in generated.latest_version.requirement_coverage.unsupported
    }
    assert {"cloud infrastructure", "deployment"} <= unsupported


def test_only_ready_proof_artifacts_cross_the_provider_boundary(
    writing_integration_fixture: RichPackageFixture,
) -> None:
    fixture = writing_integration_fixture
    with SessionLocal() as session:
        artifact = ProofArtifactService(user_id=fixture.user_id).create(
            session,
            ProofArtifactCreateRequest(
                source_memory_id=fixture.seeded.gas_memory_id,
                target_role="Data Science Intern",
            ),
        )

    provider = _MockProvider()
    service = ApplicationPackageService(
        user_id=fixture.user_id,
        settings=_settings(),
        writing_provider=provider,
    )
    package_id = _create_package(
        service,
        fixture,
        target_description="Analyze scientific data and communicate findings.",
    )
    with SessionLocal() as session:
        service.generate(session, package_id)

    assert provider.calls[0].proof_artifacts == []

    with SessionLocal() as session:
        ProofArtifactService(user_id=fixture.user_id).update(
            session,
            artifact.id,
            ProofArtifactUpdateRequest(status=ProofArtifactStatus.READY),
        )
        service.regenerate(session, package_id)

    assert [item.artifact_id for item in provider.calls[1].proof_artifacts] == [
        str(artifact.id)
    ]
