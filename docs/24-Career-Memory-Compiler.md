# Career Memory Compiler

## Why the compiler exists

An approved Career Memory may begin as a short resume-level description and
later gain reviewed project evidence. Reading only the original summary leaves
useful methods, findings, limitations, and outputs buried. Copying every detail
into a draft directly makes the opposite mistake: raw source text can leak into
the wrong section, cross project boundaries, or sound stronger than the
evidence supports.

The Career Memory Compiler is the deterministic interpretation layer between
approved memory and generated career materials. It answers:

- what this memory is really about;
- which facts and claims are supported;
- which project the evidence belongs to;
- how the same proof is relevant to a target role;
- what must not be claimed; and
- which sections still need stronger evidence.

The resulting profile is the primary input to Proof Artifact Builder and the
shared factual input for approved project memories in diagnosis and application
intelligence. It is also designed for later reuse by resume, cover-letter, and
interview workflows without making any derived interpretation into canonical
fact.

## Architecture

```text
Raw evidence
  -> review proposal
  -> approved canonical memory
  -> approved enrichment
  -> compiled career memory profile
       -> proof artifact
       -> diagnosis intelligence
       -> application intelligence
       -> future resume, cover-letter, and interview consumers
```

Compilation is transient and compile-on-read. CareerOS does not persist a
second authoritative copy of the memory profile. Each compilation reads the
current approved records, applies deterministic rules, and returns a structured
profile. A saved proof-artifact version remains a historical snapshot, while a
later regeneration compiles the latest approved state again.

The compiler runs in local deterministic mode and does not require an LLM API
key.

## Authoritative identity and user boundary

`memory_id` is authoritative. The compiler does not choose a project from title
similarity after the caller supplies an ID.

For a compilation to proceed:

1. the selected canonical memory must exist;
2. it must belong to the current user;
3. its review proposal must still be approved; and
4. every enrichment, evidence reference, and outcome signal must pass the same
   user and selected-memory checks.

An enrichment is eligible only when its `canonical_memory_id` equals the exact
selected memory ID and its status is `APPROVED`. A high-confidence title match
is not permission to borrow evidence from another memory.

This keeps Gas Kinematics and UNICORN separate. A Gas profile may state that its
boundary excludes UNICORN, but it cannot acquire UNICORN image-inspection or
t-SNE methods. A UNICORN profile may state that it is separate from Gas
Kinematics, but it cannot acquire H-alpha, GALFIT, or gas-velocity methods.
Cross-project facts require an explicitly approved enrichment attached to the
selected memory.

## Trust model

The compiler keeps five categories distinct:

| Category | Purpose | May support factual claims? |
| --- | --- | --- |
| Approved canonical memory | Current user-approved identity and facts | Yes |
| Approved enrichment | Reviewed, source-backed detail for that exact memory | Yes |
| Outcome signal | Approved feedback about what happened or what framing worked | No; strategy only |
| Target-role interpretation | Derived explanation of why approved proof matters for a role | No; framing only |
| Unsupported claim | Plausible-sounding detail without approved support | No; emit a warning or missing-evidence note |

The compiler may use linked, resolvable evidence to explain provenance and
confidence. An evidence row owned by another user, an evidence ID attached only
to another memory, or a dangling evidence ID cannot support the profile.

## Included and excluded inputs

Included inputs are:

- the selected user-owned approved canonical memory;
- its structured fields and linked user-owned evidence references;
- `APPROVED` enrichments attached to that exact memory;
- linked evidence references from those approved enrichments;
- approved outcome feedback eligible for the selected memory, represented only
  as strategy signals; and
- an optional target role or program, used only for interpretation.

Excluded inputs are:

- proposed, rejected, or archived enrichments;
- duplicate proposals that were never approved as enrichment;
- evidence linked only to a different memory;
- another user's memory, enrichment, evidence, feedback, or diagnosis;
- proposed or archived feedback events;
- target-role text presented as if it were factual proof; and
- tools, datasets, metrics, methods, findings, or outcomes that merely sound
  likely for the project.

## Compiled profile contract

The compiler returns a `CompiledCareerMemoryProfile`. Its fields are:

| Field | Meaning |
| --- | --- |
| `memory_id` | Authoritative selected canonical-memory ID |
| `canonical_title` | Approved memory title |
| `memory_type` | Canonical memory type |
| `project_kind` | Deterministic project pattern, such as Gas Kinematics, UNICORN, or generic |
| `project_boundary` | Concise statement of what belongs to this memory and what does not |
| `aliases` | Supported alternate names for this same memory |
| `source_confidence` | Confidence inherited from approved source material |
| `research_question_or_problem` | Clean statement of the supported question or problem |
| `data_or_inputs` | Supported datasets, observations, files, or other inputs |
| `methods` | Supported analysis and project methods |
| `tools` | Explicitly supported tools or technical systems |
| `workflow_steps` | Supported sequence of work |
| `findings_or_results` | Supported results, including inconclusive results |
| `limitations` | Supported constraints, caveats, and failure modes |
| `outputs` | Supported posters, reports, presentations, repositories, or other deliverables |
| `collaborators_or_context` | Supported program, institution, team, or project context |
| `role_relevance` | General transferable relevance |
| `role_relevance_by_target` | Deterministic relevance statements for known target families |
| `skills_demonstrated` | Skills evidenced by the approved facts |
| `proof_claims` | Safe factual claims suitable for proof generation |
| `resume_bullet_claims` | Approved-memory-based claim ingredients, not a newly generated resume |
| `cover_letter_angles` | Safe positioning angles, not a newly generated cover letter |
| `proof_artifact_angles` | Recommended artifact emphasis |
| `warnings_not_to_claim` | Explicit unsupported or overreaching claims to avoid |
| `evidence_used` | Classified, human-readable provenance entries |
| `evidence_ids_used` | Resolved evidence IDs used during compilation |
| `enrichment_ids_used` | Exact approved enrichment IDs used |
| `outcome_signal_ids_used` | Exact approved feedback IDs used as strategy signals |
| `outcome_signals` | Signal summaries with an explicit non-causality caveat |
| `missing_or_weak_sections` | Evidence gaps that limit downstream quality |
| `confidence` | Overall bounded confidence in the compiled profile |
| `target_role_interpretation` | Derived target-specific framing, never factual proof |
| `compiler_version` | Deterministic compiler version for inspection and regression testing |

Empty or weak sections remain visible through `missing_or_weak_sections`.
CareerOS should say what evidence is missing rather than fill the field with an
invented detail.

## Deterministic project intelligence

The compiler uses bounded vocabulary and evidence patterns. A recognized term
is included only when it appears in approved canonical material, linked
evidence, or an approved enrichment for the selected memory.

### Gas Kinematics

Supported evidence can establish a project boundary such as an honors capstone
about gas kinematics and three-dimensional galaxy morphology, separate from
UNICORN.

Depending on the approved text, the compiler can identify:

- the question of whether H-alpha gas velocity dispersion helps interpret
  high-redshift galaxy morphology or relates to the GALFIT axis ratio `b/a`;
- CEERS and RUBIES;
- JWST/NIRSpec spectroscopy and JWST/NIRCam imaging;
- GALFIT axis ratios, spectral data, and imaging data;
- catalog crossmatching by right ascension and declination;
- redshift-guided H-alpha identification;
- Gaussian fitting and nearby `[NII]` components;
- conversion of line width to gas velocity dispersion;
- instrumental-broadening correction, uncertainty propagation, covariance
  errors, S/N filtering, manual inspection, and quality cuts;
- `sigma_gas` versus `b/a` plots and low-/high-mass comparisons;
- no clear overall trend, substantial scatter, or a clearer expected trend in a
  high-mass bin when those findings are documented; and
- limitations such as sample size, slit-galaxy misalignment, turbulence,
  feedback, mergers, disturbed gas motion, unresolved kinematics, or fits that
  require manual judgment.

An inconclusive result is framed as careful hypothesis testing and uncertainty
reasoning, not upgraded into a successful trend and not dismissed as failure.
Supported outputs may include an honors capstone poster, URF presentation, or
technical report.

For data science, analytics, or AI targets, safe relevance can include messy
technical data, pipeline debugging, statistical modeling, validation, quality
control, uncertainty reasoning, and nuanced technical communication. The
profile warns against claiming quantified business impact, deployment, a
production ML system, or a conclusive trend without evidence.

### UNICORN

Supported evidence can establish an earlier GEVIP image-inspection,
categorization, or exploratory organization project, separate from Gas
Kinematics.

Depending on the approved text, the compiler can identify:

- astronomical or telescope imaging data;
- FITS files, inspection plots, and source or detection candidates;
- manual image and plot inspection;
- detection review, categorization, and labeling;
- t-SNE exploratory organization;
- grouping or sorting images by visual features;
- identification of spurious detections, hot pixels, noise, and artifacts;
- technical documentation or proposal review; and
- improved labeling or review efficiency only when the evidence explicitly
  supports that result.

For AI Engineer or AI Automation targets, safe relevance can include image-data
quality judgment, labeling workflow, exploratory representation learning,
dataset preparation, human-in-the-loop review, categorization thinking, and
model-readiness reasoning. The profile warns against claiming a deployed AI
model, a trained production ML system, performance gains, or Gas Kinematics
methods without approved support.

## Target-role interpretation

Target-role text changes emphasis, not history. The compiler may explain why a
supported method demonstrates data cleaning for a Data Scientist role or
human-in-the-loop data quality for an AI Engineer role. It cannot add a tool,
dataset, method, metric, or result because the job description requests it.

Compiling the same memory for two roles should preserve factual sections and
provenance while changing only fields such as `role_relevance_by_target`,
`proof_artifact_angles`, and `target_role_interpretation`.

## Proof Artifact Builder integration

Proof Artifact Builder uses the compiled profile as its primary generation
input. The selected memory ID used for compilation must equal the artifact's
`source_memory_id`.

The builder converts structured fields into clean case-study prose. It should
not paste a raw resume paragraph into Problem or treat target-role language as
evidence. Evidence references, enrichment IDs, signal IDs, warnings, compiler
version, and missing sections remain inspectable in the generated snapshot.

Reviewer questions are target-aware. For example:

- Gas plus Data Scientist asks whether data cleaning, modeling, validation, and
  uncertainty reasoning are clear in the first 30 seconds.
- UNICORN plus AI Engineer asks whether data-quality and labeling-workflow
  thinking for AI systems is clear in the first 30 seconds.

Changing the selected memory, target role, artifact type, or target channel
invalidates the visible preview. The workspace clears the active artifact or
shows a new-draft state that says:

> Generate a new artifact for the selected memory.

A saved Gas artifact remains available in history, but it cannot remain visible
as if it belongs to a newly selected UNICORN memory.

## Diagnosis and application integration

Diagnosis and application intelligence also compile approved project memories
before using their factual content. Diagnosis uses compiled factual text and
target-role interpretation when evaluating evidence and recommending the next
proof sprint. Application intelligence uses the profile when ranking project
matches and when assembling the approved-memory view passed into draft inputs.

Both consumers retain the same boundary as proof generation: canonical facts
and approved enrichments may support claims, while outcome signals remain
strategy-only and target-role text remains interpretation-only. Application
match provenance includes the compiled evidence and enrichment IDs so the richer
project detail stays inspectable rather than becoming an untraceable draft fact.
Non-project memories continue through their existing approved-memory paths.

## Duplicate enrichment response

Submitting evidence that is already saved for the selected project does not
create another enrichment. The create endpoint returns HTTP `409` with a
structured detail object:

```json
{
  "detail": {
    "code": "DUPLICATE_ENRICHMENT",
    "message": "This evidence already appears to be saved for this project. No duplicate enrichment was created.",
    "existing_enrichment_id": "<uuid>",
    "existing_status": "APPROVED"
  }
}
```

The frontend keeps the pasted input, displays the message next to it, and keeps
or highlights the referenced enrichment. Editing the input clears the warning;
successfully saving different evidence clears both the warning and the input.

## Missing evidence and unsupported claims

Typical missing or weak sections include:

- a quantified result;
- clearer tool-specific evidence;
- a documented output or link;
- a specific dataset or input;
- a supported limitation; or
- enough project-specific text to distinguish the work from a resume summary.

These are readiness signals, not invitations to invent content. A target-role
interpretation may recommend gathering a metric or link, but the missing item
cannot appear in `proof_claims` until approved evidence supports it.

## Downstream reuse and non-goals

Sprint 13.1 wires the compiled profile into proof, diagnosis, and application
intelligence for approved project memories. Future resume, cover-letter, and
interview workflows may reuse the same contract.

Sprint 13.1 does not add a full Resume Builder or Cover Letter Builder. The
`resume_bullet_claims` and `cover_letter_angles` fields are safe, reusable
ingredients. They remain constrained by the selected memory, evidence trail,
warnings, and approval state.

The compiler also does not add semantic embeddings, unrestricted generative
reasoning, automatic memory merging, figure interpretation, or permission to
publish an artifact without user review.
