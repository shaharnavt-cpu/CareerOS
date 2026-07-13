# Proof Artifact Builder

## What a proof artifact is

A proof artifact is a role-specific work sample built from one approved Career
Memory. It makes one supported claim easy for an evaluator to recognize:

> This approved memory proves I can do X for this target role.

Proof Artifact Builder turns Career Diagnosis into a concrete output instead of
ending with advice. The product loop is:

`Diagnosis -> Recognition gap -> 7-day Proof Sprint -> Proof Artifact`

The primary Sprint 12 artifact is a skimmable one-page case study. CareerOS also
creates channel-specific versions from the same approved facts, so the user can
reuse one evidence trail without producing unrelated drafts.

## Trust boundary

Factual claims come from the selected `canonical_memory_records` row and its
linked evidence. A pending, rejected, or otherwise unapproved review proposal is
not an eligible source.

The builder preserves:

- the source memory ID;
- the source diagnosis result ID when one is supplied;
- evidence IDs, source labels, and available evidence excerpts;
- approved outcome-signal IDs used for strategy guidance;
- warnings, readiness, generator version, and structured sections.

A target role changes how approved proof is framed. It does not become evidence.
Similarly, a diagnosis is derived guidance, not a new factual source.

If no approved memory exists, the API returns:

> Approve career memories before building a proof artifact.

## Proof and outcome signals

Canonical Career Memory and outcome feedback serve different purposes:

- **Canonical proof** supports factual claims about the user's work, methods,
  skills, inputs, findings, and documented outcomes.
- **Outcome signals** may suggest that an artifact or framing worked once. They
  can guide how the proof is presented, but they do not prove skill or causality.

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

When no outcome is documented, the artifact says that it demonstrates the
analytical process and communication of findings and warns against claiming a
quantified business outcome.

## Deterministic generation

`ProofArtifactService` uses generator version
`local-deterministic-proof-v0`. It does not require an LLM key.

Generation reads:

- one user-owned approved canonical memory;
- linked evidence and source metadata;
- a required target role or program;
- a target audience and artifact type;
- an optional diagnosis result that references the selected memory;
- eligible approved outcome signals.

The service then derives a claim, role relevance, method, limitations,
structured case-study sections, primary text, and supporting variants. It does
not mutate Career Memory, diagnosis, evidence, or feedback.

Sprint 13 adds approved project enrichment to the canonical-memory projection.
When present, the builder gives enriched problem, input, method, finding,
limitation, context, relevance, and warning fields priority over thin
resume-level summaries. Proposed, rejected, and archived enrichment is not part
of that projection and cannot guide generation. The builder links to
`/enrichments` when a project needs deeper proof.

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

Warnings identify what the user should not claim. Only resolvable, user-owned
evidence contributes to readiness, even though the saved version preserves the
source memory's full evidence-ID list for audit. Depending on the source, warnings
cover:

- missing evidence IDs;
- missing documented outcomes;
- absent approved performance metrics;
- unsupported tools, datasets, metrics, outcomes, or business impact;
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

Copied case-study content includes a compact Evidence Used section with source
labels and evidence IDs. The print view is the v0 path for printing or using the browser's **Save as
PDF** feature. Sprint 12 does not add a server-side PDF renderer or a hosted
portfolio platform.

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
- Outcome signals are sparse and cannot establish causality.
- v0 exposes the latest version rather than a full visual version history.
- Browser printing is the only PDF path.
- CareerOS does not host public portfolios or repositories.

Future work may add visual version comparison, selective evidence controls,
reviewer collaboration, richer templates, accessible branded PDF exports,
portfolio publishing integrations, and outcome-linked artifact analytics.
