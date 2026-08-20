"""Compile one approved Career Memory into provenance-aware project intelligence."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import (
    CanonicalMemoryRecord,
    CareerFeedbackEvent,
    CareerMemoryEnrichment,
    ListeningEvidence,
    ListeningSource,
    ReviewProposal,
)
from app.schemas.career_memory import (
    CompiledCareerMemoryProfile,
    CompiledEvidence,
    CompiledEvidenceKind,
    CompiledOutcomeSignal,
)
from app.schemas.diagnosis import FeedbackEventStatus
from app.schemas.enrichments import EnrichmentStatus
from app.schemas.knowledge import DEMO_USER_ID, DurableReviewStatus


class CareerMemoryCompilationError(LookupError):
    """Raised when a selected memory is unavailable or outside the trust boundary."""


@dataclass
class _ProjectDetails:
    project_boundary: str
    research_question_or_problem: str | None = None
    data_or_inputs: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    workflow_steps: list[str] = field(default_factory=list)
    findings_or_results: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    collaborators_or_context: list[str] = field(default_factory=list)
    skills_demonstrated: list[str] = field(default_factory=list)
    proof_claims: list[str] = field(default_factory=list)
    resume_bullet_claims: list[str] = field(default_factory=list)
    cover_letter_angles: list[str] = field(default_factory=list)
    proof_artifact_angles: list[str] = field(default_factory=list)
    warnings_not_to_claim: list[str] = field(default_factory=list)


class CareerMemoryCompiler:
    """Turn approved factual layers into a deterministic, target-aware profile."""

    compiler_version = "career-memory-compiler-v1"
    _non_factual_keys = {
        "alias",
        "aliases",
        "approved enrichment ids",
        "cover letter angles",
        "project name",
        "project title",
        "proof artifact angles",
        "proof artifact summary",
        "resume bullet claims",
        "role relevance",
        "role specific framing",
        "title",
        "warnings not to claim",
    }

    def __init__(self, user_id: uuid.UUID = DEMO_USER_ID) -> None:
        self.user_id = user_id

    def compile(
        self,
        session: Session,
        memory_id: uuid.UUID,
        target_role: str | None = None,
    ) -> CompiledCareerMemoryProfile:
        """Compile only the explicitly selected approved memory and its layers."""

        memory = self._approved_memory(session, memory_id)
        all_enrichments = session.scalars(
            select(CareerMemoryEnrichment)
            .where(
                CareerMemoryEnrichment.user_id == self.user_id,
                CareerMemoryEnrichment.canonical_memory_id == memory.id,
            )
            .order_by(
                CareerMemoryEnrichment.created_at,
                CareerMemoryEnrichment.id,
            )
        ).all()
        approved_enrichments = [
            item
            for item in all_enrichments
            if item.status == EnrichmentStatus.APPROVED.value
        ]
        canonical_fields = self._canonical_fields(memory.structured_fields)
        field_sets = [
            canonical_fields,
            *(item.structured_enrichment for item in approved_enrichments),
        ]
        evidence_records, canonical_ids, enrichment_evidence_ids = (
            self._resolved_evidence(
                session,
                memory,
                all_enrichments,
                approved_enrichments,
            )
        )
        factual_text = self._factual_text(
            field_sets,
            evidence_records,
        )
        aliases = self._aliases(memory, canonical_fields)
        project_kind = self._project_kind(memory, aliases)
        if project_kind == "GAS_KINEMATICS":
            details = self._compile_gas(factual_text, field_sets)
        elif project_kind == "UNICORN":
            details = self._compile_unicorn(factual_text, field_sets)
        else:
            details = self._compile_generic(memory, factual_text, field_sets)

        approved_warnings = self._field_values(
            field_sets,
            "warnings_not_to_claim",
        )
        details.warnings_not_to_claim = self._unique(
            [*details.warnings_not_to_claim, *approved_warnings]
        )
        role_relevance_by_target = self._role_relevance_by_target(
            project_kind,
            details,
        )
        role_relevance, target_interpretation = self._target_interpretation(
            target_role,
            role_relevance_by_target,
        )
        outcome_signals = self._outcome_signals(session, memory.id)
        evidence_used = self._compiled_evidence(
            session,
            memory,
            canonical_fields,
            evidence_records,
            set(canonical_ids),
            set(enrichment_evidence_ids),
            approved_enrichments,
        )
        missing = self._missing_sections(details, factual_text)
        confidence = self._profile_confidence(
            memory,
            approved_enrichments,
            details,
            bool(evidence_records),
        )
        return CompiledCareerMemoryProfile(
            memory_id=memory.id,
            canonical_title=memory.title,
            memory_type=memory.memory_type,
            project_kind=project_kind,
            project_boundary=details.project_boundary,
            aliases=aliases,
            source_confidence=float(memory.confidence),
            research_question_or_problem=details.research_question_or_problem,
            data_or_inputs=details.data_or_inputs,
            methods=details.methods,
            tools=details.tools,
            workflow_steps=details.workflow_steps,
            findings_or_results=details.findings_or_results,
            limitations=details.limitations,
            outputs=details.outputs,
            collaborators_or_context=details.collaborators_or_context,
            role_relevance=role_relevance,
            role_relevance_by_target=role_relevance_by_target,
            skills_demonstrated=details.skills_demonstrated,
            proof_claims=details.proof_claims,
            resume_bullet_claims=details.resume_bullet_claims,
            cover_letter_angles=details.cover_letter_angles,
            proof_artifact_angles=details.proof_artifact_angles,
            warnings_not_to_claim=details.warnings_not_to_claim,
            evidence_used=evidence_used,
            evidence_ids_used=[str(item.id) for item in evidence_records],
            enrichment_ids_used=[item.id for item in approved_enrichments],
            outcome_signal_ids_used=[
                item.feedback_event_id for item in outcome_signals
            ],
            outcome_signals=outcome_signals,
            missing_or_weak_sections=missing,
            confidence=confidence,
            target_role_interpretation=target_interpretation,
            compiler_version=self.compiler_version,
        )

    def _approved_memory(
        self,
        session: Session,
        memory_id: uuid.UUID,
    ) -> CanonicalMemoryRecord:
        memory = session.scalar(
            select(CanonicalMemoryRecord)
            .join(
                ReviewProposal,
                ReviewProposal.id == CanonicalMemoryRecord.review_proposal_id,
            )
            .where(
                CanonicalMemoryRecord.id == memory_id,
                CanonicalMemoryRecord.user_id == self.user_id,
                ReviewProposal.user_id == self.user_id,
                ReviewProposal.decision.in_(
                    (
                        DurableReviewStatus.APPROVED.value,
                        DurableReviewStatus.EDITED_APPROVED.value,
                    )
                ),
            )
        )
        if memory is None:
            raise CareerMemoryCompilationError(
                "Approved Career Memory was not found for compilation."
            )
        return memory

    @classmethod
    def _canonical_fields(cls, fields: dict[str, Any]) -> dict[str, Any]:
        """Remove the compatibility projection before reading enrichment rows."""

        return {
            key: value
            for key, value in fields.items()
            if not key.startswith("enriched_")
            and not key.startswith("_enrichment_")
            and key != "approved_enrichment_ids"
        }

    def _resolved_evidence(
        self,
        session: Session,
        memory: CanonicalMemoryRecord,
        all_enrichments: list[CareerMemoryEnrichment],
        approved_enrichments: list[CareerMemoryEnrichment],
    ) -> tuple[list[ListeningEvidence], list[str], list[str]]:
        base_ids = memory.structured_fields.get("_enrichment_base_evidence_ids")
        if isinstance(base_ids, list):
            canonical_ids = [str(item) for item in base_ids]
        else:
            excluded = {
                str(evidence_id)
                for enrichment in all_enrichments
                if enrichment.status != EnrichmentStatus.APPROVED.value
                for evidence_id in enrichment.evidence_ids
            }
            canonical_ids = [
                str(item) for item in memory.evidence_ids if str(item) not in excluded
            ]
        enrichment_ids = [
            str(evidence_id)
            for enrichment in approved_enrichments
            for evidence_id in enrichment.evidence_ids
        ]
        ordered_ids = self._unique([*canonical_ids, *enrichment_ids])
        records: list[ListeningEvidence] = []
        for evidence_id in ordered_ids:
            try:
                record = session.get(ListeningEvidence, uuid.UUID(evidence_id))
            except (TypeError, ValueError):
                continue
            if record is not None and record.user_id == self.user_id:
                records.append(record)
        return records, canonical_ids, enrichment_ids

    @classmethod
    def _factual_text(
        cls,
        field_sets: list[dict[str, Any]],
        evidence_records: list[ListeningEvidence],
    ) -> str:
        # Canonical identity selects the project kind and establishes the boundary,
        # but it is not evidence for a method, finding, or transferable skill.
        parts: list[str] = []
        for fields in field_sets:
            parts.extend(cls._factual_field_text(fields))
        parts.extend(item.raw_excerpt for item in evidence_records)
        return "\n".join(part for part in parts if part.strip())

    @classmethod
    def _factual_field_text(cls, fields: dict[str, Any]) -> list[str]:
        parts: list[str] = []
        for key, value in fields.items():
            normalized = key.casefold().replace("_", " ")
            if (
                normalized in cls._non_factual_keys
                or normalized.startswith("warning")
                or normalized.startswith("target role")
                or key.startswith("_")
            ):
                continue
            if isinstance(value, dict):
                parts.extend(cls._factual_field_text(value))
            elif isinstance(value, list):
                parts.extend(str(item) for item in value if cls._has_value(item))
            elif cls._has_value(value):
                parts.append(str(value))
        return parts

    @classmethod
    def _aliases(
        cls,
        memory: CanonicalMemoryRecord,
        canonical_fields: dict[str, Any],
    ) -> list[str]:
        aliases = cls._field_values(
            [canonical_fields],
            "aliases",
            "alias",
            "project_name",
            "project_title",
        )
        identity = " ".join((memory.title, memory.identity_key)).casefold()
        if "gas" in identity and "kinematic" in identity:
            aliases.append("Gas Kinematics")
        if re.search(r"\bunicorn\b", identity):
            aliases.append("UNICORN")
        return [
            item
            for item in cls._unique(aliases)
            if item.casefold() != memory.title.casefold()
        ]

    @staticmethod
    def _project_kind(
        memory: CanonicalMemoryRecord,
        aliases: list[str],
    ) -> str:
        """Classify from canonical identity only, never from another evidence corpus."""

        identity = " ".join((memory.title, memory.identity_key, *aliases)).casefold()
        if re.search(r"\bunicorn\b", identity):
            return "UNICORN"
        if "gas" in identity and (
            "kinematic" in identity or "galax" in identity or "morpholog" in identity
        ):
            return "GAS_KINEMATICS"
        return "GENERIC_PROJECT" if memory.memory_type == "PROJECT" else "GENERIC"

    @classmethod
    def _compile_gas(
        cls,
        factual_text: str,
        field_sets: list[dict[str, Any]],
    ) -> _ProjectDetails:
        text = factual_text.casefold()
        details = _ProjectDetails(
            project_boundary=(
                "Honors capstone / Gas Kinematics project. Separate from UNICORN."
                if "honors" in text or "capstone" in text
                else "Gas Kinematics project. Separate from UNICORN."
            )
        )
        has_h_alpha = cls._has_h_alpha(text)
        has_axis_ratio = cls._has_axis_ratio(text)
        has_velocity_dispersion = "velocity dispersion" in text or "sigma_gas" in text
        if has_h_alpha and has_axis_ratio and has_velocity_dispersion:
            details.research_question_or_problem = (
                "The project tested whether H-alpha gas velocity dispersion could "
                "help evaluate 3D galaxy morphology estimates from imaging-based "
                "axis ratios (b/a)."
            )
        elif "gas kinematic" in text and "morpholog" in text:
            redshift = (
                "high-redshift "
                if "high-redshift" in text or "high redshift" in text
                else ""
            )
            details.research_question_or_problem = (
                "The project investigated whether gas kinematics could help "
                f"interpret the 3D morphology of {redshift}galaxies."
            )
        else:
            details.research_question_or_problem = cls._first_field_text(
                field_sets,
                "research_question",
                "project_goal",
                "problem",
                "objective",
                "goal",
                "summary",
            )

        details.data_or_inputs = cls._supported_labels(
            text,
            (
                ("CEERS catalog and observations", (r"\bceers\b",)),
                ("RUBIES catalog and observations", (r"\brubies\b",)),
                ("JWST/NIRSpec spectroscopy", (r"nirspec",)),
                ("JWST/NIRCam imaging", (r"nircam",)),
                ("spectral data", (r"spectr(?:a|al|oscopy)",)),
                ("imaging data", (r"\bimag(?:e|es|ing)\b",)),
            ),
        )
        if "galfit" in text:
            details.data_or_inputs.append(
                "GALFIT axis ratios (b/a)"
                if has_axis_ratio
                else "GALFIT measurements"
            )
        elif has_axis_ratio:
            details.data_or_inputs.append("imaging-based axis ratios (b/a)")
        method_rules = (
            (
                "catalog crossmatching by RA/DEC",
                (r"cross[- ]?match", r"ra\s*/\s*dec|right ascension"),
                "all",
            ),
            (
                "redshift-guided H-alpha line identification",
                (r"redshift", r"h[- ]?alpha|hα"),
                "all",
            ),
            ("Gaussian fitting", (r"gaussian fit",), "any"),
            ("[NII] component fitting", (r"\[n\s*ii\]|\bn\s*ii\b",), "any"),
            (
                "line-width to gas velocity-dispersion conversion",
                (r"line width|line-width", r"velocity dispersion|sigma_gas"),
                "all",
            ),
            (
                "instrumental broadening correction",
                (r"instrumental broadening|instrument resolution",),
                "any",
            ),
            (
                "uncertainty and error propagation",
                (r"uncertaint|error propagation|propagated error",),
                "any",
            ),
            (
                "covariance-matrix error estimation (p_cov diagonal)",
                (r"covariance|p_cov|p cov",),
                "any",
            ),
            ("S/N filtering", (r"\bs\s*/\s*n\b|signal[- ]to[- ]noise",), "any"),
            (
                "manual visual inspection and quality cuts",
                (r"manual(?:ly)?|visual inspection", r"quality cut|fit trust|inspect"),
                "all",
            ),
            (
                "sigma_gas versus b/a visualization",
                (r"sigma_gas|σ\s*gas", r"\bb/a\b|axis ratio"),
                "all",
            ),
            ("mass-bin comparison", (r"mass bin|mass-bin",), "any"),
            ("statistical analysis", (r"statistical analys",), "any"),
            ("statistical modeling", (r"statistical model",), "any"),
            ("modeling", (r"\bmodeling\b|\bmodelling\b",), "any"),
            ("data visualization", (r"visuali[sz]|plotting",), "any"),
            (
                "technical communication",
                (r"communicat|present(?:ed|ation)|poster",),
                "any",
            ),
        )
        details.methods = cls._supported_methods(text, method_rules)
        if "statistical modeling" in details.methods and "modeling" in details.methods:
            details.methods.remove("modeling")
        details.tools = cls._supported_labels(
            text,
            (
                ("JWST/NIRSpec", (r"nirspec",)),
                ("JWST/NIRCam", (r"nircam",)),
                ("GALFIT", (r"galfit",)),
                ("Python", (r"\bpython\b",)),
            ),
        )
        workflow_map = {
            "catalog crossmatching by RA/DEC": "Crossmatched catalogs by RA/DEC.",
            "redshift-guided H-alpha line identification": (
                "Used redshift information to identify the H-alpha line."
            ),
            "Gaussian fitting": (
                "Fit supported emission-line components with Gaussian models."
            ),
            "[NII] component fitting": (
                "Reviewed nearby [NII] components in the line fit."
            ),
            "line-width to gas velocity-dispersion conversion": (
                "Converted fitted line widths to gas velocity dispersion."
            ),
            "instrumental broadening correction": (
                "Corrected supported measurements for instrumental broadening."
            ),
            "uncertainty and error propagation": (
                "Propagated uncertainty through the supported measurements."
            ),
            "covariance-matrix error estimation (p_cov diagonal)": (
                "Used covariance-matrix information to estimate fit errors."
            ),
            "S/N filtering": "Applied signal-to-noise filtering.",
            "manual visual inspection and quality cuts": (
                "Visually inspected fits and applied quality cuts."
            ),
            "sigma_gas versus b/a visualization": (
                "Plotted sigma_gas versus imaging axis ratio (b/a)."
            ),
            "mass-bin comparison": (
                "Compared the supported measurements across mass bins."
            ),
        }
        details.workflow_steps = [
            workflow_map[item] for item in details.methods if item in workflow_map
        ]

        no_clear = bool(re.search(r"no clear (?:overall )?trend|inconclusive", text))
        scatter = "significant scatter" in text or "large scatter" in text
        if no_clear and scatter:
            details.findings_or_results.append(
                "The overall comparison showed no clear trend and significant scatter."
            )
        elif no_clear:
            details.findings_or_results.append(
                "The analysis found no clear overall trend and remained inconclusive."
            )
        elif scatter:
            details.findings_or_results.append(
                "The supported comparison showed significant scatter."
            )
        if "low-mass" in text or "low mass" in text:
            if "high-mass" in text or "high mass" in text:
                details.findings_or_results.append(
                    "The analysis compared low- and high-mass bins."
                )
        if (
            ("high-mass" in text or "high mass" in text)
            and "expected trend" in text
            and any(term in text for term in ("clearer", "only", "emerg"))
        ):
            details.findings_or_results.append(
                "The expected trend appeared clearer only in the high-mass bin."
            )

        details.limitations = cls._supported_labels(
            text,
            (
                (
                    "limited sample size",
                    (r"limited sample|small sample|sample size",),
                ),
                (
                    "slit-galaxy misalignment",
                    (r"slit.{0,20}misalign|misalign.{0,20}slit",),
                ),
                (
                    "turbulence, feedback, mergers, or disturbed gas motions",
                    (r"turbulen|feedback|merger|disturbed gas",),
                ),
                (
                    "unresolved high-redshift kinematics",
                    (r"unresolved.{0,30}kinematic|spatial resolution",),
                ),
                (
                    "some fits required manual trust and quality judgments",
                    (r"problematic fit|fit trust|manual(?:ly)?.{0,20}fit",),
                ),
            ),
        )
        details.outputs = cls._gas_outputs(text)
        if "honors" in text or "capstone" in text:
            details.collaborators_or_context.append("Honors capstone context")
        details.skills_demonstrated = cls._unique(
            [
                *(
                    ["complex technical data analysis"]
                    if details.data_or_inputs
                    else []
                ),
                *(
                    ["pipeline validation and quality control"]
                    if any(
                        item in details.methods
                        for item in (
                            "S/N filtering",
                            "manual visual inspection and quality cuts",
                            "instrumental broadening correction",
                        )
                    )
                    else []
                ),
                *(
                    ["statistical modeling"]
                    if "statistical modeling" in details.methods
                    else []
                ),
                *(
                    ["modeling"]
                    if "modeling" in details.methods
                    and "statistical modeling" not in details.methods
                    else []
                ),
                *(
                    ["uncertainty reasoning"]
                    if any(
                        "uncert" in item.casefold() or "covariance" in item.casefold()
                        for item in details.methods
                    )
                    else []
                ),
                *(
                    ["careful hypothesis testing"]
                    if details.findings_or_results
                    else []
                ),
                *(
                    ["technical communication"]
                    if details.outputs or "presentation" in text or "poster" in text
                    else []
                ),
            ]
        )
        details.proof_claims = cls._gas_proof_claims(details)
        details.resume_bullet_claims = cls._gas_resume_claims(details)
        if cls._has_rich_gas_details(details):
            details.cover_letter_angles = [
                "Use the project to show disciplined hypothesis testing, validation, "
                "and clear communication of uncertainty without overstating the "
                "result."
            ]
            details.proof_artifact_angles = [
                "Lead with the galaxy-morphology question, the linked spectroscopy "
                "and imaging inputs, the quality-controlled workflow, and the "
                "careful result."
            ]
        else:
            details.cover_letter_angles = [
                "Add approved method and result evidence before using this project "
                "for a strong role-specific claim."
            ]
            details.proof_artifact_angles = [
                "Keep the artifact explicit about which problem, method, and result "
                "details are still missing."
            ]
        details.warnings_not_to_claim = [
            "Do not claim quantified business impact without approved evidence.",
            "Do not claim model deployment or a production ML system.",
            "Do not claim a conclusive trend when the approved evidence says there "
            "was no clear trend.",
        ]
        return cls._dedupe_details(details)

    @classmethod
    def _compile_unicorn(
        cls,
        factual_text: str,
        field_sets: list[dict[str, Any]],
    ) -> _ProjectDetails:
        text = factual_text.casefold()
        boundary_prefix = (
            "Earlier GEVIP UNICORN project" if "gevip" in text else "UNICORN project"
        )
        if any(
            term in text for term in ("image inspection", "categor", "detection review")
        ):
            boundary_prefix += " focused on image inspection and categorization"
        details = _ProjectDetails(
            project_boundary=f"{boundary_prefix}. Separate from Gas Kinematics."
        )
        if any(
            term in text
            for term in (
                "organize",
                "organise",
                "inspect",
                "categor",
                "label",
                "review",
            )
        ) and any(
            term in text for term in ("image", "imaging", "detection", "telescope")
        ):
            details.research_question_or_problem = (
                "The project focused on organizing, inspecting, and reviewing "
                "astronomical imaging or detection data for reliable categorization."
            )
        else:
            details.research_question_or_problem = cls._first_field_text(
                field_sets,
                "research_question",
                "project_goal",
                "problem",
                "objective",
                "goal",
                "summary",
            )
        details.data_or_inputs = cls._supported_labels(
            text,
            (
                ("astronomical imaging data", (r"astronomical imag|telescope imag",)),
                ("FITS files", (r"\bfits\b",)),
                ("inspection plots", (r"inspection plot",)),
                (
                    "detection or source candidates",
                    (r"detection candidate|source candidate|detections",),
                ),
            ),
        )
        details.methods = cls._supported_methods(
            text,
            (
                (
                    "manual inspection of plots and images",
                    (r"manual(?:ly)?(?: inspect| review)|image inspection",),
                    "any",
                ),
                (
                    "detection review",
                    (r"detection review|review(?:ed|ing)? detections",),
                    "any",
                ),
                (
                    "categorization and labeling",
                    (r"categori[sz]|label(?:ing|led|ed)",),
                    "any",
                ),
                (
                    "t-SNE exploratory organization",
                    (r"t[- ]?sne|t-distributed stochastic neighbor",),
                    "any",
                ),
                (
                    "visual-feature grouping and sorting",
                    (r"visual feature|group(?:ed|ing)? images|sort(?:ed|ing)? images",),
                    "any",
                ),
                (
                    (
                        "identifying spurious detections, hot pixels, noise, "
                        "and artifacts"
                    ),
                    (r"spurious detection|hot pixel|noise|artifact",),
                    "any",
                ),
                (
                    "technical documentation",
                    (r"technical documentation|document(?:ed|ation) the",),
                    "any",
                ),
                (
                    "proposal review",
                    (r"proposal review|review(?:ed|ing)? proposal",),
                    "any",
                ),
            ),
        )
        details.tools = cls._supported_labels(
            text,
            (
                ("t-SNE", (r"t[- ]?sne|t-distributed stochastic neighbor",)),
                ("Python", (r"\bpython\b",)),
            ),
        )
        workflow_map = {
            "manual inspection of plots and images": (
                "Inspected plots and images manually."
            ),
            "detection review": "Reviewed source or detection candidates.",
            "categorization and labeling": "Categorized and labeled reviewed images.",
            "t-SNE exploratory organization": "Explored image organization with t-SNE.",
            "visual-feature grouping and sorting": (
                "Grouped or sorted images by supported visual features."
            ),
            ("identifying spurious detections, hot pixels, noise, and artifacts"): (
                "Flagged supported artifacts and spurious detections during quality "
                "review."
            ),
            "technical documentation": (
                "Documented the review and categorization workflow."
            ),
            "proposal review": "Reviewed the associated technical proposal.",
        }
        details.workflow_steps = [workflow_map[item] for item in details.methods]
        if re.search(
            r"improv\w*.{0,40}(?:label|review).{0,30}efficien|(?:label|review).{0,30}efficien",
            text,
        ):
            details.findings_or_results.append(
                "The approved evidence reports improved labeling or review efficiency."
            )
        if re.search(
            r"better organi[sz]|improv\w*.{0,30}(?:category|categori[sz]|organization)",
            text,
        ):
            details.findings_or_results.append(
                "The work improved the organization of image categories."
            )
        if "data quality" in text and any(
            term in text for term in ("insight", "workflow", "review")
        ):
            details.findings_or_results.append(
                "The work produced data-quality workflow insight for future review."
            )
        details.limitations = cls._unique(
            cls._field_values(field_sets, "limitations", "limitation")
        )
        details.outputs = cls._supported_labels(
            text,
            (
                ("technical documentation", (r"technical documentation",)),
                (
                    "reviewed image categories or labels",
                    (r"image categor|image label|labeled images",),
                ),
                ("inspection plots", (r"inspection plot",)),
            ),
        )
        if "gevip" in text:
            details.collaborators_or_context.append("Earlier GEVIP project context")
        details.skills_demonstrated = cls._unique(
            [
                *(
                    ["image-data quality judgment"]
                    if any(
                        "inspection" in item or "artifact" in item
                        for item in details.methods
                    )
                    else []
                ),
                *(
                    ["labeling and categorization workflow"]
                    if "categorization and labeling" in details.methods
                    else []
                ),
                *(
                    ["exploratory representation analysis"]
                    if "t-SNE exploratory organization" in details.methods
                    else []
                ),
                *(
                    ["human-in-the-loop review"]
                    if any(
                        item
                        in {
                            "manual inspection of plots and images",
                            "detection review",
                            "categorization and labeling",
                        }
                        for item in details.methods
                    )
                    else []
                ),
                *(
                    ["dataset preparation and model-readiness reasoning"]
                    if details.data_or_inputs and details.methods
                    else []
                ),
                *(
                    ["technical documentation"]
                    if "technical documentation" in details.methods
                    else []
                ),
            ]
        )
        details.proof_claims = cls._unicorn_proof_claims(details)
        details.resume_bullet_claims = cls._unicorn_resume_claims(details)
        if cls._has_rich_unicorn_details(details):
            details.cover_letter_angles = [
                "Use UNICORN to explain how careful image review, categorization, "
                "and documentation improve the data-readiness of an AI workflow."
            ]
            details.proof_artifact_angles = [
                "Frame the work as an image-data quality and human-in-the-loop "
                "review case study, naming t-SNE only when the approved evidence "
                "supports it."
            ]
        else:
            details.cover_letter_angles = [
                "Add approved image-input, review-method, and result evidence before "
                "using UNICORN for a strong AI-workflow claim."
            ]
            details.proof_artifact_angles = [
                "Keep the artifact explicit about the project details that are still "
                "missing from approved evidence."
            ]
        details.warnings_not_to_claim = [
            "Do not claim a deployed AI model unless approved evidence supports it.",
            "Do not claim a deployed or trained production ML model.",
            "Do not claim quantified performance gains without approved evidence.",
            "Do not claim Gas Kinematics methods or findings for UNICORN.",
        ]
        return cls._dedupe_details(details)

    @classmethod
    def _compile_generic(
        cls,
        memory: CanonicalMemoryRecord,
        factual_text: str,
        field_sets: list[dict[str, Any]],
    ) -> _ProjectDetails:
        details = _ProjectDetails(
            project_boundary=(
                f"This compiled profile is scoped only to {memory.title}."
            ),
            research_question_or_problem=cls._first_field_text(
                field_sets,
                "research_question",
                "project_goal",
                "problem",
                "objective",
                "goal",
                "summary",
                "description",
            ),
            data_or_inputs=cls._split_field_values(
                field_sets,
                "data_or_inputs",
                "data",
                "inputs",
                "dataset",
                "datasets",
            ),
            methods=cls._split_field_values(
                field_sets,
                "tools_or_methods",
                "analysis_steps",
                "methods",
                "method",
                "approach",
                "process",
            ),
            findings_or_results=cls._split_field_values(
                field_sets,
                "findings_or_results",
                "findings",
                "results",
                "outcome",
                "impact",
            ),
            limitations=cls._split_field_values(
                field_sets,
                "limitations",
                "limitation",
            ),
            outputs=cls._split_field_values(
                field_sets,
                "outputs",
                "output",
                "deliverables",
            ),
            collaborators_or_context=cls._split_field_values(
                field_sets,
                "collaborators_or_context",
                "context",
                "collaborators",
            ),
        )
        text = factual_text.casefold()
        details.tools = cls._supported_labels(
            text,
            (
                ("Python", (r"\bpython\b",)),
                ("SQL", (r"\bsql\b",)),
                ("R", (r"\br\b",)),
                ("Tableau", (r"\btableau\b",)),
                ("Power BI", (r"power\s+bi",)),
            ),
        )
        details.workflow_steps = [
            f"{item.rstrip('.')} .".replace(" .", ".") for item in details.methods
        ]
        details.skills_demonstrated = cls._unique(
            cls._field_values(field_sets, "skills", "skills_demonstrated")
            + details.tools
            + details.methods[:4]
        )
        if details.research_question_or_problem and details.methods:
            method_summary = cls._join(details.methods[:3])
            details.proof_claims.append(
                f"Addressed the documented project question using {method_summary}."
            )
        if details.methods:
            details.resume_bullet_claims.append(
                f"Applied {cls._join(details.methods[:3])} in {memory.title}."
            )
        details.cover_letter_angles = cls._field_values(
            field_sets,
            "cover_letter_angles",
        ) or [
            f"Use {memory.title} to explain the documented approach without adding "
            "unsupported impact."
        ]
        details.proof_artifact_angles = cls._field_values(
            field_sets,
            "proof_artifact_angles",
        ) or [
            "Lead with the documented problem, inputs, method, result, and limitations."
        ]
        details.warnings_not_to_claim = [
            "Do not add tools, datasets, metrics, or outcomes that are absent from "
            "approved evidence."
        ]
        return cls._dedupe_details(details)

    @classmethod
    def _role_relevance_by_target(
        cls,
        project_kind: str,
        details: _ProjectDetails,
    ) -> dict[str, str]:
        if project_kind == "GAS_KINEMATICS" and cls._has_rich_gas_details(
            details
        ):
            return {
                "DATA": (
                    "Evidence of working with messy technical data, building and "
                    "validating an analytical workflow, reasoning about uncertainty, "
                    "and communicating an inconclusive result without overclaiming."
                ),
                "AI": (
                    "Evidence of pipeline validation, statistical reasoning, quality "
                    "control, and careful evaluation of noisy technical measurements."
                ),
                "GENERAL": (
                    "Evidence of rigorous hypothesis testing, technical analysis, "
                    "quality control, and nuanced scientific communication."
                ),
            }
        if project_kind == "UNICORN" and cls._has_rich_unicorn_details(details):
            return {
                "AI": (
                    "Evidence of image-data quality judgment, labeling workflow, "
                    "exploratory organization, dataset preparation, and "
                    "human-in-the-loop review for AI systems."
                ),
                "DATA": (
                    "Evidence of organizing ambiguous image data, applying repeatable "
                    "quality review, and documenting categories for downstream "
                    "analysis."
                ),
                "GENERAL": (
                    "Evidence of careful image inspection, categorization, "
                    "data-quality judgment, and technical documentation."
                ),
            }
        skills = cls._join(details.skills_demonstrated[:5])
        general = (
            f"Evidence of {skills}."
            if skills
            else (
                "Approved evidence does not yet support a role-specific capability "
                "claim; add method and result detail before using this project as "
                "proof."
            )
        )
        return {"DATA": general, "AI": general, "GENERAL": general}

    @staticmethod
    def _has_rich_gas_details(details: _ProjectDetails) -> bool:
        """Require evidence coverage before emitting the full Gas role narrative."""

        methods = " ".join(details.methods).casefold()
        return bool(
            details.research_question_or_problem
            and details.data_or_inputs
            and details.findings_or_results
            and any(
                term in methods
                for term in (
                    "quality",
                    "broadening",
                    "uncertainty",
                    "covariance",
                    "s/n",
                )
            )
        )

    @staticmethod
    def _has_rich_unicorn_details(details: _ProjectDetails) -> bool:
        """Require supported image, review, labeling, and organization evidence."""

        methods = set(details.methods)
        return bool(
            details.data_or_inputs
            and "categorization and labeling" in methods
            and methods.intersection(
                {
                    "manual inspection of plots and images",
                    "detection review",
                }
            )
            and methods.intersection(
                {
                    "t-SNE exploratory organization",
                    "visual-feature grouping and sorting",
                }
            )
        )

    @classmethod
    def _target_interpretation(
        cls,
        target_role: str | None,
        role_map: dict[str, str],
    ) -> tuple[str, str | None]:
        family = cls._target_family(target_role)
        relevance = role_map.get(family, role_map["GENERAL"])
        if not target_role:
            return relevance, None
        normalized_relevance = relevance[0].lower() + relevance[1:]
        interpretation = (
            f"For {target_role.strip()}, frame this memory as {normalized_relevance} "
            "This target-role interpretation does not add factual project claims."
        )
        return relevance, interpretation

    @staticmethod
    def _target_family(target_role: str | None) -> str:
        target = (target_role or "").casefold()
        if re.search(
            r"\b(?:ai|artificial intelligence|machine learning|automation)\b", target
        ):
            return "AI"
        if re.search(r"\b(?:data|analytics?|analyst|business intelligence)\b", target):
            return "DATA"
        return "GENERAL"

    def _outcome_signals(
        self,
        session: Session,
        memory_id: uuid.UUID,
    ) -> list[CompiledOutcomeSignal]:
        records = session.scalars(
            select(CareerFeedbackEvent)
            .where(
                CareerFeedbackEvent.user_id == self.user_id,
                CareerFeedbackEvent.status == FeedbackEventStatus.APPROVED.value,
            )
            .order_by(CareerFeedbackEvent.updated_at.desc())
        ).all()
        memory_key = str(memory_id)
        return [
            CompiledOutcomeSignal(
                feedback_event_id=record.id,
                summary=record.structured_summary,
                guidance=record.suggested_future_use,
                caveat=(
                    "Approved feedback is a strategy signal, not factual proof or "
                    "evidence that this memory caused an outcome."
                ),
            )
            for record in records
            if memory_key in {str(item) for item in record.related_memory_ids}
        ]

    def _compiled_evidence(
        self,
        session: Session,
        memory: CanonicalMemoryRecord,
        canonical_fields: dict[str, Any],
        evidence_records: list[ListeningEvidence],
        canonical_ids: set[str],
        enrichment_evidence_ids: set[str],
        approved_enrichments: list[CareerMemoryEnrichment],
    ) -> list[CompiledEvidence]:
        entries = [
            CompiledEvidence(
                evidence_id=str(memory.id),
                kind=CompiledEvidenceKind.CANONICAL_MEMORY,
                source_label="Approved canonical Career Memory",
                excerpt=self._canonical_excerpt(memory, canonical_fields),
                confidence=float(memory.confidence),
            )
        ]
        for evidence in evidence_records:
            source = session.get(ListeningSource, evidence.source_id)
            if source is not None and source.user_id != self.user_id:
                source = None
            evidence_id = str(evidence.id)
            kind = (
                CompiledEvidenceKind.APPROVED_ENRICHMENT
                if evidence_id in enrichment_evidence_ids
                and evidence_id not in canonical_ids
                else CompiledEvidenceKind.CANONICAL_EVIDENCE
            )
            entries.append(
                CompiledEvidence(
                    evidence_id=evidence_id,
                    kind=kind,
                    source_label=(
                        source.label
                        if source is not None
                        else "Approved linked evidence"
                    ),
                    excerpt=evidence.raw_excerpt,
                    confidence=float(evidence.confidence),
                )
            )
        entries.extend(
            CompiledEvidence(
                evidence_id=str(enrichment.id),
                kind=CompiledEvidenceKind.APPROVED_ENRICHMENT,
                source_label=enrichment.source_label or "Approved project enrichment",
                excerpt=self._structured_excerpt(enrichment.structured_enrichment),
                confidence=float(enrichment.confidence),
            )
            for enrichment in approved_enrichments
        )
        return entries

    @classmethod
    def _canonical_excerpt(
        cls,
        memory: CanonicalMemoryRecord,
        fields: dict[str, Any],
    ) -> str:
        summary = cls._first_field_text(
            [fields],
            "summary",
            "description",
            "problem",
            "objective",
        )
        return f"{memory.title}. {summary}" if summary else memory.title

    @classmethod
    def _structured_excerpt(cls, fields: dict[str, Any]) -> str:
        values = cls._factual_field_text(fields)
        rendered = "; ".join(cls._unique(values))
        return (
            rendered
            if len(rendered) <= 3000
            else f"{rendered[:2997].rstrip()}..."
        )

    @classmethod
    def _missing_sections(
        cls,
        details: _ProjectDetails,
        factual_text: str,
    ) -> list[str]:
        missing: list[str] = []
        if not cls._has_metric(factual_text):
            missing.append("Need quantified result")
        if not details.tools:
            missing.append("Need clearer tool-specific evidence")
        if not details.outputs and not re.search(
            r"https?://|www\.", factual_text, re.I
        ):
            missing.append("Need output/link")
        if not details.research_question_or_problem:
            missing.append("Need clearer project problem")
        if not details.data_or_inputs:
            missing.append("Need clearer data/input evidence")
        if not details.methods:
            missing.append("Need clearer method evidence")
        if not details.findings_or_results:
            missing.append("Need clearer supported result")
        return missing

    @staticmethod
    def _profile_confidence(
        memory: CanonicalMemoryRecord,
        approved_enrichments: list[CareerMemoryEnrichment],
        details: _ProjectDetails,
        has_resolved_evidence: bool,
    ) -> float:
        sources = [float(memory.confidence)] + [
            float(item.confidence) for item in approved_enrichments
        ]
        source_score = sum(sources) / len(sources)
        covered = sum(
            bool(value)
            for value in (
                details.research_question_or_problem,
                details.data_or_inputs,
                details.methods,
                details.findings_or_results,
                details.limitations,
                details.outputs,
            )
        )
        coverage_score = covered / 6
        score = source_score * 0.72 + coverage_score * 0.28
        if not has_resolved_evidence and not approved_enrichments:
            score = min(score, 0.74)
        return round(min(max(score, 0), 0.99), 3)

    @classmethod
    def _gas_outputs(cls, text: str) -> list[str]:
        outputs: list[str] = []
        if "poster" in text and ("honors" in text or "capstone" in text):
            outputs.append("honors capstone poster")
        if "urf" in text and ("poster" in text or "presentation" in text):
            outputs.append("URF poster or presentation")
        if "technical report" in text:
            outputs.append("technical report")
        if "presentation" in text and not any(
            "presentation" in item for item in outputs
        ):
            outputs.append("technical presentation")
        return outputs

    @classmethod
    def _gas_proof_claims(cls, details: _ProjectDetails) -> list[str]:
        claims: list[str] = []
        if details.research_question_or_problem:
            claims.append(details.research_question_or_problem)
        if details.methods:
            claims.append(
                f"Applied {cls._join(details.methods[:5])} in the documented analysis."
            )
        claims.extend(details.findings_or_results)
        return claims

    @classmethod
    def _gas_resume_claims(cls, details: _ProjectDetails) -> list[str]:
        if not details.methods or not details.data_or_inputs:
            return []
        data = cls._join(details.data_or_inputs[:3])
        result = (
            " and communicated the inconclusive result without overstating it"
            if details.findings_or_results
            else ""
        )
        return [f"Analyzed {data} using {cls._join(details.methods[:4])}{result}."]

    @classmethod
    def _unicorn_proof_claims(cls, details: _ProjectDetails) -> list[str]:
        claims: list[str] = []
        if details.research_question_or_problem:
            claims.append(details.research_question_or_problem)
        if details.methods:
            method_summary = cls._join(details.methods[:5])
            workflow = (
                "image-review workflow"
                if details.data_or_inputs
                and any(
                    item
                    in {
                        "manual inspection of plots and images",
                        "detection review",
                        "categorization and labeling",
                    }
                    for item in details.methods
                )
                else "UNICORN workflow"
            )
            claims.append(
                f"Applied {method_summary} to the documented {workflow}."
            )
        claims.extend(details.findings_or_results)
        return claims

    @classmethod
    def _unicorn_resume_claims(cls, details: _ProjectDetails) -> list[str]:
        if not details.methods or not details.data_or_inputs:
            return []
        method_summary = cls._join(details.methods[:4])
        inputs = cls._join(details.data_or_inputs[:3])
        return [
            f"Reviewed and organized {inputs} using {method_summary}."
        ]

    @classmethod
    def _dedupe_details(cls, details: _ProjectDetails) -> _ProjectDetails:
        for name in (
            "data_or_inputs",
            "methods",
            "tools",
            "workflow_steps",
            "findings_or_results",
            "limitations",
            "outputs",
            "collaborators_or_context",
            "skills_demonstrated",
            "proof_claims",
            "resume_bullet_claims",
            "cover_letter_angles",
            "proof_artifact_angles",
            "warnings_not_to_claim",
        ):
            setattr(details, name, cls._unique(getattr(details, name)))
        return details

    @staticmethod
    def _has_h_alpha(text: str) -> bool:
        return bool(re.search(r"h\s*[- ]?\s*alpha|hα", text, re.I))

    @staticmethod
    def _has_axis_ratio(text: str) -> bool:
        return bool(re.search(r"\bb\s*/\s*a\b|axis ratio", text, re.I))

    @staticmethod
    def _has_metric(text: str) -> bool:
        return bool(
            re.search(
                r"(?<!\w)\d+(?:\.\d+)?\s*(?:%|percent\b|x\b|samples?\b|records?\b|objects?\b)",
                text,
                re.I,
            )
        )

    @classmethod
    def _supported_labels(
        cls,
        text: str,
        rules: Iterable[tuple[str, tuple[str, ...]]],
    ) -> list[str]:
        return [
            label
            for label, patterns in rules
            if any(re.search(pattern, text, re.I) for pattern in patterns)
        ]

    @classmethod
    def _supported_methods(
        cls,
        text: str,
        rules: Iterable[tuple[str, tuple[str, ...], str]],
    ) -> list[str]:
        methods: list[str] = []
        for label, patterns, mode in rules:
            matches = [bool(re.search(pattern, text, re.I)) for pattern in patterns]
            if (mode == "all" and all(matches)) or (mode == "any" and any(matches)):
                methods.append(label)
        return methods

    @classmethod
    def _first_field_text(
        cls,
        field_sets: list[dict[str, Any]],
        *keys: str,
    ) -> str | None:
        values = cls._field_values(field_sets, *keys)
        return cls._clean_statement(values[0]) if values else None

    @classmethod
    def _split_field_values(
        cls,
        field_sets: list[dict[str, Any]],
        *keys: str,
    ) -> list[str]:
        split: list[str] = []
        for value in cls._field_values(field_sets, *keys):
            pieces = re.split(r"\n+|\s*;\s*|\s*,\s*(?=[A-Za-z])", value)
            split.extend(cls._clean_statement(item) for item in pieces if item.strip())
        return cls._unique(split)

    @classmethod
    def _field_values(
        cls,
        field_sets: list[dict[str, Any]],
        *keys: str,
    ) -> list[str]:
        wanted = {key.casefold().replace("_", " ") for key in keys}
        values: list[str] = []
        for fields in field_sets:
            values.extend(cls._find_field_values(fields, wanted))
        return cls._unique(values)

    @classmethod
    def _find_field_values(
        cls,
        fields: dict[str, Any],
        wanted: set[str],
    ) -> list[str]:
        values: list[str] = []
        for key, value in fields.items():
            normalized = key.casefold().replace("_", " ")
            if normalized in wanted:
                if isinstance(value, list):
                    values.extend(str(item) for item in value if cls._has_value(item))
                elif cls._has_value(value):
                    values.append(str(value))
            if isinstance(value, dict):
                values.extend(cls._find_field_values(value, wanted))
        return values

    @staticmethod
    def _clean_statement(value: str) -> str:
        cleaned = " ".join(value.strip(" -*\t").split())
        cleaned = re.sub(r"^[^:]{2,40}:\s*", "", cleaned)
        if len(cleaned) > 500:
            sentence = re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)[0]
            cleaned = (
                sentence if len(sentence) <= 500 else f"{sentence[:497].rstrip()}..."
            )
        return cleaned

    @staticmethod
    def _has_value(value: Any) -> bool:
        return value not in (None, "", [], {})

    @staticmethod
    def _unique(values: Iterable[Any]) -> list[str]:
        unique: list[str] = []
        seen: set[str] = set()
        for value in values:
            rendered = " ".join(str(value).split()).strip()
            if not rendered:
                continue
            key = rendered.casefold()
            if key in seen:
                continue
            seen.add(key)
            unique.append(rendered)
        return unique

    @staticmethod
    def _join(values: list[str]) -> str:
        if not values:
            return ""
        if len(values) == 1:
            return values[0]
        if len(values) == 2:
            return f"{values[0]} and {values[1]}"
        return f"{', '.join(values[:-1])}, and {values[-1]}"


def compile_career_memory(
    memory_id: uuid.UUID,
    target_role: str | None = None,
    user_id: uuid.UUID | None = None,
    session: Session | None = None,
) -> CompiledCareerMemoryProfile:
    """Convenience entry point for callers with or without an existing session."""

    compiler = CareerMemoryCompiler(user_id=user_id or DEMO_USER_ID)
    if session is not None:
        return compiler.compile(session, memory_id, target_role)
    with SessionLocal() as owned_session:
        return compiler.compile(owned_session, memory_id, target_role)


def compiled_profile_factual_fields(
    profile: CompiledCareerMemoryProfile,
) -> dict[str, Any]:
    """Project a profile into factual buckets safe for downstream generation."""

    return {
        "title": profile.canonical_title,
        "research_question_or_problem": profile.research_question_or_problem,
        "data_or_inputs": profile.data_or_inputs,
        "methods": profile.methods,
        "tools": profile.tools,
        "workflow_steps": profile.workflow_steps,
        "findings_or_results": profile.findings_or_results,
        "limitations": profile.limitations,
        "outputs": profile.outputs,
        "collaborators_or_context": profile.collaborators_or_context,
        "skills": profile.skills_demonstrated,
        "proof_claims": profile.proof_claims,
        "resume_bullet_claims": profile.resume_bullet_claims,
    }


def compiled_profile_factual_text(profile: CompiledCareerMemoryProfile) -> str:
    """Flatten factual profile fields without role interpretation or feedback."""

    factual = compiled_profile_factual_fields(profile)
    factual["evidence_excerpts"] = [
        item.excerpt for item in profile.evidence_used if item.excerpt
    ]
    return json.dumps(factual, ensure_ascii=False)
