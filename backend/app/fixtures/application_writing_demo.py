"""Fictional Build Week application-writing fixture.

Maya Chen and every organization, project, and target below are synthetic.  The
fixture intentionally contains no contact details or other personal identifiers.
"""

from app.services.application_writing_provider import (
    ApplicationQuestionInput,
    ApplicationWritingDataClassification,
    ApplicationWritingDataSource,
    ApplicationWritingInput,
    ApplicationWritingRequirements,
    ApprovedEnrichmentInput,
    ApprovedEvidenceAtom,
    ClaimCertainty,
    EvidenceAtomSupportType,
    MissingProofWarningInput,
    ProofArtifactInput,
    SelectedCompiledMemory,
    StrategyOutcomeSignal,
    StructuredOutcome,
)


def build_maya_chen_demo_writing_input() -> ApplicationWritingInput:
    """Return a fresh, strictly validated fictional provider input."""

    return ApplicationWritingInput(
        target_role="Data Science Intern",
        company="Northstar Insights",
        job_description=(
            "Northstar Insights is seeking a Data Science Intern to analyze complex "
            "datasets, build reproducible Python workflows, validate data quality, "
            "and communicate findings to technical and nontechnical partners. SQL "
            "and dashboard experience are preferred. Cloud deployment is a plus."
        ),
        grouped_requirements=ApplicationWritingRequirements(
            must_have=[
                "data analysis",
                "reproducible analytical workflows",
                "data quality",
                "communicating findings",
            ],
            preferred=["SQL", "dashboard development", "cloud deployment"],
            technical=["Python", "statistical modeling", "quality control"],
            communication=["technical communication", "explaining results"],
            concrete_tools_requiring_direct_proof=["Python", "SQL", "AWS"],
            broad_semantic_concepts=[
                "analytics",
                "reporting",
                "modeling",
                "data quality",
            ],
        ),
        central_responsibilities=[
            "Analyze structured scientific datasets",
            "Check data and model quality",
            "Explain findings to mixed audiences",
        ],
        application_questions=[
            ApplicationQuestionInput(
                question_id="motivation",
                question_text=(
                    "Why are you interested in this Data Science internship?"
                ),
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
        ],
        selected_memories=[
            SelectedCompiledMemory(
                memory_id="demo-memory-scientific-analysis",
                title="Scientific Data Research Project",
                memory_type="PROJECT",
                summary=(
                    "Designed a reproducible analysis to test whether spectroscopic "
                    "measurements could improve estimates derived from images."
                ),
                approved_claims=[
                    "Built a Python workflow joining spectroscopy and imaging tables.",
                    (
                        "Used statistical fitting and uncertainty checks to evaluate "
                        "results."
                    ),
                    (
                        "Documented an inconclusive result without overstating the "
                        "evidence."
                    ),
                ],
                skills_and_tools=["Python", "statistical analysis"],
                methods=[
                    "catalog matching",
                    "statistical fitting",
                    "uncertainty analysis",
                ],
                outcomes=[
                    "Produced a reproducible analysis and clearly bounded conclusion."
                ],
                evidence_reference_ids=[
                    "demo-evidence-analysis-workflow",
                    "demo-evidence-uncertainty-review",
                ],
                confidence=0.98,
            ),
            SelectedCompiledMemory(
                memory_id="demo-memory-image-quality",
                title="Image Categorization and Data Quality Project",
                memory_type="PROJECT",
                summary=(
                    "Reviewed image collections, refined categories, and documented "
                    "ambiguous cases for a consistent data-quality workflow."
                ),
                approved_claims=[
                    "Created a repeatable visual-review and categorization process.",
                    "Flagged ambiguous examples instead of forcing uncertain labels.",
                ],
                skills_and_tools=["quality control", "data categorization"],
                methods=["visual inspection", "label review", "categorization"],
                outcomes=["Improved consistency of the reviewed image collection."],
                evidence_reference_ids=["demo-evidence-image-quality"],
                confidence=0.96,
            ),
            SelectedCompiledMemory(
                memory_id="demo-memory-peer-teaching",
                title="Peer Analytics Teaching",
                memory_type="EXPERIENCE",
                summary=(
                    "Led small peer sessions that translated analytical concepts into "
                    "clear examples and step-by-step explanations."
                ),
                approved_claims=[
                    "Explained analytical concepts to peers with varied experience.",
                    "Adapted examples in response to questions and confusion.",
                ],
                skills_and_tools=["technical communication", "peer teaching"],
                outcomes=["Helped peers work through unfamiliar analytical concepts."],
                evidence_reference_ids=["demo-evidence-peer-teaching"],
                confidence=0.94,
            ),
        ],
        evidence_ledger=[
            ApprovedEvidenceAtom(
                evidence_atom_id="atom-target-role",
                approved_claim_id="claim-target-role",
                support_type=EvidenceAtomSupportType.TARGET_CONTEXT,
                factual_statement=(
                    "The fictional target is a Data Science Intern role at "
                    "Northstar Insights."
                ),
                allowed_certainty=ClaimCertainty.ASPIRATIONAL,
                prohibited_expansions=[
                    "Do not treat target-role wording as candidate experience."
                ],
            ),
            ApprovedEvidenceAtom(
                evidence_atom_id="atom-scientific-python-workflow",
                canonical_memory_id="demo-memory-scientific-analysis",
                approved_claim_id="claim-scientific-python-workflow",
                evidence_reference_ids=["demo-evidence-analysis-workflow"],
                support_type=EvidenceAtomSupportType.DIRECT,
                factual_statement=(
                    "Built a Python workflow joining spectroscopy and imaging tables."
                ),
                supported_tools=["Python"],
                supported_methods=["catalog matching"],
                allowed_certainty=ClaimCertainty.OBSERVED,
                prohibited_expansions=[
                    "SQL experience",
                    "cloud deployment",
                    "production machine-learning deployment",
                ],
            ),
            ApprovedEvidenceAtom(
                evidence_atom_id="atom-scientific-uncertainty",
                canonical_memory_id="demo-memory-scientific-analysis",
                approved_claim_id="claim-scientific-uncertainty",
                evidence_reference_ids=["demo-evidence-uncertainty-review"],
                support_type=EvidenceAtomSupportType.DIRECT,
                factual_statement=(
                    "Used statistical fitting and uncertainty checks to evaluate "
                    "results."
                ),
                supported_methods=[
                    "statistical fitting",
                    "uncertainty analysis",
                ],
                allowed_certainty=ClaimCertainty.QUALIFIED,
                prohibited_expansions=[
                    "causal proof",
                    "quantified business impact",
                ],
            ),
            ApprovedEvidenceAtom(
                evidence_atom_id="atom-scientific-bounded-outcome",
                canonical_memory_id="demo-memory-scientific-analysis",
                approved_claim_id="claim-scientific-bounded-outcome",
                evidence_reference_ids=["demo-evidence-uncertainty-review"],
                support_type=EvidenceAtomSupportType.DIRECT,
                factual_statement=(
                    "Produced a reproducible analysis and clearly bounded conclusion."
                ),
                supported_outcome=StructuredOutcome(
                    evidence_source_id="demo-evidence-uncertainty-review",
                    action="produced",
                    object="reproducible analysis and bounded conclusion",
                    outcome=(
                        "Produced a reproducible analysis and clearly bounded "
                        "conclusion."
                    ),
                    qualifier="without overstating an inconclusive result",
                    certainty=ClaimCertainty.QUALIFIED,
                ),
                allowed_certainty=ClaimCertainty.QUALIFIED,
                prohibited_expansions=[
                    "conclusive trend",
                    "causal proof",
                    "business impact",
                ],
            ),
            ApprovedEvidenceAtom(
                evidence_atom_id="atom-image-quality-process",
                canonical_memory_id="demo-memory-image-quality",
                approved_claim_id="claim-image-quality-process",
                evidence_reference_ids=["demo-evidence-image-quality"],
                support_type=EvidenceAtomSupportType.DIRECT,
                factual_statement=(
                    "Created a repeatable visual-review and categorization process."
                ),
                supported_methods=[
                    "visual inspection",
                    "label review",
                    "categorization",
                ],
                allowed_certainty=ClaimCertainty.OBSERVED,
                prohibited_expansions=[
                    "model accuracy",
                    "production deployment",
                    "quantified performance gain",
                ],
            ),
            ApprovedEvidenceAtom(
                evidence_atom_id="atom-image-review-consistency",
                canonical_memory_id="demo-memory-image-quality",
                approved_claim_id="claim-image-review-consistency",
                evidence_reference_ids=["demo-evidence-image-quality"],
                support_type=EvidenceAtomSupportType.DIRECT,
                factual_statement=(
                    "Improved consistency of the reviewed image collection."
                ),
                supported_outcome=StructuredOutcome(
                    evidence_source_id="demo-evidence-image-quality",
                    action="improved",
                    object="consistency of the reviewed image collection",
                    outcome="Improved consistency of the reviewed image collection.",
                    qualifier="qualitative review result",
                    certainty=ClaimCertainty.OBSERVED,
                ),
                allowed_certainty=ClaimCertainty.OBSERVED,
                prohibited_expansions=[
                    "model accuracy",
                    "causal proof",
                    "quantified performance gain",
                ],
            ),
            ApprovedEvidenceAtom(
                evidence_atom_id="atom-peer-teaching",
                canonical_memory_id="demo-memory-peer-teaching",
                approved_claim_id="claim-peer-teaching",
                evidence_reference_ids=["demo-evidence-peer-teaching"],
                support_type=EvidenceAtomSupportType.DIRECT,
                factual_statement=(
                    "Explained analytical concepts to peers with varied experience."
                ),
                supported_methods=["peer teaching", "technical communication"],
                allowed_certainty=ClaimCertainty.OBSERVED,
                prohibited_expansions=[
                    "formal people management",
                    "quantified learning outcome",
                ],
            ),
            ApprovedEvidenceAtom(
                evidence_atom_id="atom-enrichment-analysis-validation",
                canonical_memory_id="demo-memory-scientific-analysis",
                enrichment_id="demo-enrichment-analysis-validation",
                approved_claim_id="claim-enrichment-analysis-validation",
                evidence_reference_ids=["demo-evidence-uncertainty-review"],
                support_type=EvidenceAtomSupportType.APPROVED_ENRICHMENT,
                factual_statement=(
                    "The workflow included input checks, fit review, and uncertainty "
                    "reasoning before the result was interpreted."
                ),
                supported_methods=["input checks", "fit review"],
                allowed_certainty=ClaimCertainty.QUALIFIED,
                prohibited_expansions=["causal proof", "conclusive result"],
            ),
            ApprovedEvidenceAtom(
                evidence_atom_id="atom-enrichment-quality-decisions",
                canonical_memory_id="demo-memory-image-quality",
                enrichment_id="demo-enrichment-quality-decisions",
                approved_claim_id="claim-enrichment-quality-decisions",
                evidence_reference_ids=["demo-evidence-image-quality"],
                support_type=EvidenceAtomSupportType.APPROVED_ENRICHMENT,
                factual_statement=(
                    "Unclear images were flagged for review instead of receiving "
                    "unsupported labels."
                ),
                supported_methods=["ambiguous-case review"],
                allowed_certainty=ClaimCertainty.OBSERVED,
                prohibited_expansions=["automated labeling", "model monitoring"],
            ),
            ApprovedEvidenceAtom(
                evidence_atom_id="atom-proof-analytics-case-study",
                canonical_memory_id="demo-memory-scientific-analysis",
                proof_artifact_id="demo-proof-analytics-case-study",
                approved_claim_id="claim-proof-analytics-case-study",
                support_type=EvidenceAtomSupportType.PROOF_ARTIFACT,
                factual_statement=(
                    "A fictional case study documents workflow design, validation, "
                    "and careful interpretation."
                ),
                supported_methods=["workflow validation"],
                allowed_certainty=ClaimCertainty.QUALIFIED,
                prohibited_expansions=["production deployment"],
            ),
            ApprovedEvidenceAtom(
                evidence_atom_id="atom-proof-data-quality-brief",
                canonical_memory_id="demo-memory-image-quality",
                proof_artifact_id="demo-proof-data-quality-brief",
                approved_claim_id="claim-proof-data-quality-brief",
                support_type=EvidenceAtomSupportType.PROOF_ARTIFACT,
                factual_statement=(
                    "A fictional work sample documents categorization rules and "
                    "ambiguous-case review."
                ),
                supported_methods=["categorization", "ambiguous-case review"],
                allowed_certainty=ClaimCertainty.QUALIFIED,
                prohibited_expansions=["production model", "quantified accuracy"],
            ),
            ApprovedEvidenceAtom(
                evidence_atom_id="atom-scientific-framing",
                canonical_memory_id="demo-memory-scientific-analysis",
                approved_claim_id="claim-scientific-framing",
                evidence_reference_ids=["demo-evidence-analysis-workflow"],
                support_type=EvidenceAtomSupportType.INFERRED_FRAMING,
                factual_statement=(
                    "The scientific project may be framed as relevant analytical "
                    "experience without adding new facts."
                ),
                allowed_certainty=ClaimCertainty.QUALIFIED,
                prohibited_expansions=[
                    "Do not use framing as direct proof of a tool or outcome."
                ],
            ),
        ],
        approved_enrichment=[
            ApprovedEnrichmentInput(
                enrichment_id="demo-enrichment-analysis-validation",
                memory_id="demo-memory-scientific-analysis",
                label="Analysis validation detail",
                content=(
                    "The workflow included input checks, fit review, and uncertainty "
                    "reasoning before the result was interpreted."
                ),
                evidence_reference_ids=["demo-evidence-uncertainty-review"],
            ),
            ApprovedEnrichmentInput(
                enrichment_id="demo-enrichment-quality-decisions",
                memory_id="demo-memory-image-quality",
                label="Ambiguous-case handling",
                content=(
                    "Unclear images were flagged for review and recorded separately "
                    "rather than assigned unsupported labels."
                ),
                evidence_reference_ids=["demo-evidence-image-quality"],
            ),
        ],
        proof_artifacts=[
            ProofArtifactInput(
                artifact_id="demo-proof-analytics-case-study",
                title="Scientific Analytics Case Study",
                artifact_type="CASE_STUDY",
                summary=(
                    "A fictional demo case study showing workflow design, validation, "
                    "and careful interpretation."
                ),
                memory_ids=["demo-memory-scientific-analysis"],
            ),
            ProofArtifactInput(
                artifact_id="demo-proof-data-quality-brief",
                title="Data Quality Review Brief",
                artifact_type="WORK_SAMPLE",
                summary=(
                    "A fictional demo brief showing categorization rules and ambiguous "
                    "case review."
                ),
                memory_ids=["demo-memory-image-quality"],
            ),
        ],
        outcome_signals=[
            StrategyOutcomeSignal(
                signal_id="demo-signal-role-emphasis",
                label="Role-emphasis signal",
                content=(
                    "Emphasize disciplined analysis, quality control, and "
                    "communication."
                ),
            )
        ],
        prohibited_claims=[
            "SQL experience",
            "AWS experience",
            "cloud deployment",
            "production machine-learning deployment",
        ],
        missing_proof_warnings=[
            MissingProofWarningInput(
                requirement="SQL",
                explanation=(
                    "The selected demo memories do not directly prove SQL experience."
                ),
            ),
            MissingProofWarningInput(
                requirement="cloud deployment",
                explanation=(
                    "No selected demo memory supports cloud or deployment experience."
                ),
            ),
        ],
        desired_tone="direct, professional, and internship-appropriate",
        desired_output_length="concise resume bullets and a 250-400 word cover letter",
        generator_version="build-week-demo-fixture-v1",
        data_classification=ApplicationWritingDataClassification(
            profile_id="build-week-demo-maya-chen",
            profile_name="Maya Chen",
            is_demo=True,
            source=ApplicationWritingDataSource.SEEDED_FICTIONAL,
        ),
    )
