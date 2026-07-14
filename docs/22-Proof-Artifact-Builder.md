# Proof Artifact Builder

## What a proof artifact is

A proof artifact is a role-specific work sample built from one compiled,
approved Career Memory. It makes one supported claim easy for an evaluator to
recognize:

> This approved memory proves I can do X for this target role.

Proof Artifact Builder turns Career Diagnosis into a concrete output instead of
ending with advice. The product loop is:

`Diagnosis -> Recognition gap -> 7-day Proof Sprint -> Proof Artifact`

The primary Sprint 12 artifact is a skimmable one-page case study. CareerOS also
creates channel-specific versions from the same approved facts, so the user can
reuse one evidence trail without producing unrelated drafts.

## Trust boundary

Factual claims come from a transient compiled profile for the exact selected
`canonical_memory_records` row. The Career Memory Compiler combines that
user-owned approved memory, its linked evidence, and only `APPROVED` enrichment
records attached to the same memory ID. A pending, rejected, archived, foreign,
or otherwise unapproved record is not an eligible source.

The selected memory ID is authoritative. Title similarity cannot redirect
generation or borrow facts from another project. Gas Kinematics and UNICORN may
share broad astronomy context, but their data, methods, findings, outputs,
evidence IDs, and enrichment IDs remain separate unless an approved enrichment
explicitly links the fact to the selected memory.

The builder preserves:

- the source memory ID;
- the source diagnosis result ID when one is supplied;
- evidence IDs, source labels, and available evidence excerpts;
- approved enrichment IDs and compiler version used for the generated snapshot;
- approved outcome-signal IDs used for strategy guidance;
- warnings, readiness, generator version, and structured sections.

A target role changes how approved proof is framed. It does not become evidence.
Similarly, a diagnosis is derived guidance, not a new factual source.

If no approved memory exists, the API returns:

> Approve career memories before building a proof artifact.

## Proof and outcome signals

Canonical Career Memory, approved enrichment, and outcome feedback serve
different purposes:

- **Canonical proof** supports factual claims about the user's work, methods,
  skills, inputs, findings, and documented outcomes.
- **Approved enrichment** adds reviewed, source-backed factual detail to that
  exact memory. It can strengthen proof without creating another project.
- **Outcome signals** may suggest that an artifact or framing worked once. They
  can guide how the proof is presented, but they do not prove skill or causality.
- **Target-role interpretation** changes emphasis and reviewer language. It is
  derived framing, not factual evidence.

Only approved `ARTIFACT_SUCCESS` feedback events may be included. The event must
either be captured in the selected diagnosis result or be directly linked to the
selected memory. Archived feedback is excluded. Signals appear in their own
response field and section and carry a causality caveat such as:

> An approved outcome note suggests similar framing worked once. This is a
> strategy signal, not proof of causality.

Outcome event IDs are never promoted into the artifact's evidence ID list.

## Supported artifact types

Sprint 12 supports these saved artifact types:

- `CASE_STUDY`
- `GITHUB_README`
- `PORTFOLIO_PAGE`
- `APPLICATION_UPLOAD`
- `OUTREACH_SUMMARY`
- `INTERVIEW_STORY`
- `RESUME_BULLETS`

`CASE_STUDY`, `PORTFOLIO_PAGE`, and `APPLICATION_UPLOAD` use the full case-study
content as their primary text. The other types use the matching channel variant
as primary content. Every generated version also includes a common supporting
variant set:

- two resume bullets;
- a cover-letter paragraph;
- an outreach blurb;
- an interview answer;
- a GitHub README outline.

These variants share the same source memory, evidence IDs, claim, limitations,
and warnings.

## Supported target audiences

The selected audience determines the recommended use and reviewer prompt:

- `APPLICATION_UPLOAD`
- `PORTFOLIO`
- `GITHUB`
- `OUTREACH`
- `INTERVIEW_PREP`
- `GENERAL`

For example, an application-upload artifact is framed as an optional work
sample, while an interview-prep artifact emphasizes a supported story and the
details the user should be ready to explain.

## One-page case study structure

The deterministic case-study template contains:

1. Title
2. Target claim
3. Role relevance
4. Context
5. Problem
6. Data or inputs
7. Method
8. Evidence used
9. Skills demonstrated
10. Outcome or insight
11. Limitations
12. What this proves
13. How to use
14. Reviewer question

The builder favors role-relevant capabilities over an unexplained domain label.
For an analytics target, the approved Gas Kinematics memory can foreground data
analysis, modeling, uncertainty or error propagation, and technical
communication when those details appear in approved memory or linked evidence.
It must not add Python, a dataset name, a result, or a metric merely because such
a detail would sound plausible.

With richer approved Gas evidence, the compiled profile can produce clean prose
about supported CEERS/RUBIES inputs, JWST/NIRSpec spectroscopy, JWST/NIRCam
imaging, GALFIT `b/a`, H-alpha fitting, uncertainty handling, quality cuts, and
`sigma_gas` versus `b/a`. With approved UNICORN evidence, an AI-targeted artifact
can instead emphasize image inspection, categorization, t-SNE exploration,
labeling workflow, data-quality judgment, and technical documentation. The
builder cannot transfer either project's details into the other artifact.

When no outcome is documented, the artifact says that it demonstrates the
analytical process and communication of findings and warns against claiming a
quantified business outcome.

## Deterministic generation

`ProofArtifactService` uses generator version
`local-deterministic-proof-v0`. It does not require an LLM key.

Generation first asks the transient Career Memory Compiler to read:

- one user-owned approved canonical memory;
- linked, user-owned evidence and source metadata;
- only `APPROVED` enrichments attached to that exact memory;
- a required target role or program;
- eligible approved outcome feedback as strategy signals only.

The builder then combines the compiled profile with a target audience and
artifact type and, when supplied, an optional diagnosis result that references
the selected memory. The compiler is deterministic, compile-on-read, and not a
new persistent source-of-truth table.

The service derives a claim, role relevance, method, limitations, structured
case-study sections, primary text, reviewer question, and supporting variants
from the compiled fields. It converts supported facts into clean case-study
prose instead of dumping raw resume or project text into Problem. It does not
mutate Career Memory, enrichment, diagnosis, evidence, or feedback.

Sprint 13.1 makes the compiled profile the builder's primary input. Proposed,
rejected, and archived enrichment cannot influence it. Approved outcome feedback
is returned separately with a strategy-only, non-causality caveat. Target-role
text may change interpretation and reviewer wording but cannot introduce a new
tool, dataset, method, result, or metric. The builder links to `/enrichments`
when a project needs deeper proof.

## Readiness and warnings

Each version has a readiness score from `0.0` to `1.0` and one label:

- `NEEDS_EVIDENCE`
- `DRAFTABLE`
- `STRONG_DRAFT`
- `READY_TO_SHARE`

The deterministic score considers evidence count, claim clarity, method detail,
role-relevant capabilities, and whether an outcome is documented. A memory with
no evidence cannot score above the needs-evidence range. A missing documented
outcome prevents the generator from treating the artifact as fully ready.

Compiler-identified gaps remain explicit. Examples include `Need quantified
result`, `Need clearer tool-specific evidence`, and `Need output/link`. These
gaps lower readiness or guide enrichment; they are never permission to invent a
missing fact.

Warnings identify what the user should not claim. Only resolvable, user-owned
evidence contributes to readiness, even though the saved version preserves the
source memory's full evidence-ID list for audit. Depending on the source, warnings
cover:

- missing evidence IDs;
- missing documented outcomes;
- absent approved performance metrics;
- unsupported tools, datasets, metrics, outcomes, or business impact;
- unsupported deployment, production-ML, or cross-project claims;
- the difference between an outcome signal and causal proof.

When edited content adds numeric claims not found in approved memory or its
evidence trail, the version receives a verification warning and its readiness is
capped at `DRAFTABLE` until the claim is removed or supported.

Readiness is guidance, not an automatic publishing decision. The user controls
the artifact status.

## Persistence and versioning

`proof_artifacts` stores artifact identity and lifecycle metadata:

- user, title, type, target role, and target audience;
- selected source memory;
- optional source diagnosis result;
- `DRAFT`, `REVIEWED`, `READY`, or `ARCHIVED` status;
- created and updated timestamps.

`proof_artifact_versions` stores generated and edited content:

- monotonically increasing version number;
- title, claim, primary content, and structured sections;
- evidence IDs and outcome-signal IDs;
- warnings, readiness score, and readiness label;
- supporting variants;
- created and updated timestamps.

The structured snapshot also preserves the compiler version and the evidence,
approved enrichment, and outcome-signal references used to create that version.
The compiled profile itself remains transient and is not a second canonical
record.

Initial generation creates version 1. Regeneration appends a new version, uses
the latest approved evidence and feedback, and returns the artifact to `DRAFT`.
If regeneration changes the target role, the old diagnosis link is cleared so
provenance does not imply that the prior diagnosis evaluated the new target.
Editing saves changes to the latest version in place; older versions are immutable
through the v0 API. Title and target-claim edits remain synchronized with their
structured sections and rendered headings. The v0 read model returns the latest
version and total version count. Full version-history browsing is future work.

Saved artifact snapshots remain readable if the source proposal later leaves the
approved state. That preserves the historical artifact; regeneration still
requires the source memory to be currently approved.

## API

All endpoints are scoped to the current user:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/proof-artifacts/eligible-memories` | List approved memories available to the builder. |
| `POST` | `/api/proof-artifacts` | Generate and save a new artifact with version 1. |
| `GET` | `/api/proof-artifacts` | List saved artifacts with their latest version. |
| `GET` | `/api/proof-artifacts/{id}` | Read one artifact and its latest version. |
| `POST` | `/api/proof-artifacts/{id}/regenerate` | Generate and append the next version. |
| `PATCH` | `/api/proof-artifacts/{id}` | Update title or status. Target-role and audience changes must use regeneration so generated content cannot become stale. |
| `PATCH` | `/api/proof-artifacts/{id}/versions/{version_id}` | Save edits to version content, sections, or variants. |

Supplying a diagnosis result is optional. When present, it must belong to the
same user and reference the selected memory. Missing resources return `404`;
invalid source relationships or missing approved memory return `422`.

## Workspace and export behavior

The `/proof-artifacts` workspace lets the user:

- select an approved memory;
- choose a target role, artifact type, and audience;
- generate or reopen a saved artifact;
- inspect evidence, source labels, outcome signals, warnings, and readiness;
- edit and save the generated content;
- regenerate a new version;
- mark an artifact reviewed or ready, or archive it;
- copy the primary case-study text and supporting variants;
- open a print-friendly view.

Memory, target role, artifact type, and target channel define the current draft
selection. Changing any of them while a saved artifact is open clears the active
preview or shows a new-draft state:

> Generate a new artifact for the selected memory.

The saved artifact remains in history, but a Gas artifact cannot stay visible as
if it belongs to a newly selected UNICORN memory. A response generated for an
older selection must not replace a newer selection if the controls change while
generation is in flight.

Copied case-study content includes a compact Evidence Used section with readable
source labels and excerpts; internal evidence IDs remain linked without being
dumped into user-facing prose. The print view is the v0 path for printing or
using the browser's **Save as PDF** feature. Sprint 12 does not add a server-side
PDF renderer or a hosted portfolio platform.

## Ways to use an artifact

- Attach the case study as an optional application work sample.
- Publish reviewed text on a portfolio page.
- Use the README outline to explain a repository quickly.
- Reference the target claim in a cover letter.
- Send the short blurb in personalized outreach.
- Practice the evidence-backed interview answer.
- Ask a target-aware reviewer whether the role value is clear in 30 seconds.

## Limitations and future work

- Generation is deterministic and intentionally narrow; it does not perform
  open-ended rewriting.
- Readiness measures evidence completeness and draft safety, not employer
  approval or hiring likelihood.
- Source quality limits artifact quality.
- Deterministic compiler patterns are bounded and do not understand every
  project domain.
- Outcome signals are sparse and cannot establish causality.
- v0 exposes the latest version rather than a full visual version history.
- Browser printing is the only PDF path.
- CareerOS does not host public portfolios or repositories.

Future work may add visual version comparison, selective evidence controls,
reviewer collaboration, richer templates, accessible branded PDF exports,
portfolio publishing integrations, and outcome-linked artifact analytics. Sprint
13.1 already uses compiled project memory in proof, diagnosis, and application
intelligence, but does not add a full resume or cover-letter generator; it
exposes safe claim ingredients those future builders can consume under the same
evidence boundary.
