# Proof Artifact Builder v0

## Status

Implemented in Sprint 12. CareerOS can turn one approved canonical Career
Memory into a durable, role-specific proof artifact using local deterministic
generation. Artifacts preserve evidence provenance, warnings, readiness, and
optional approved outcome signals. They can be edited, regenerated into new
versions, reviewed, marked ready, archived, copied, and printed.

The primary v0 output is a one-page case study. Channel-specific variants are
derived from that same artifact and evidence trail.

## Problem

Career Diagnosis can identify a recognition gap and recommend a seven-day proof
sprint, but a recommendation such as "package this project as recognizable
proof" still leaves the user to design the work sample alone.

Overlooked students often have relevant proof already. The missing step is not
another generic project or resume rewrite; it is a concise artifact that makes
approved work legible to a particular evaluator.

## Goal

Given one approved canonical memory, a target role or program, and a target
audience, CareerOS should produce a saved, editable, honest artifact that makes
one supported claim obvious:

> This approved memory proves I can do X for this target role.

Sprint 12 makes the North Star loop action-producing:

`Diagnosis -> Proof Sprint -> Proof Artifact -> Use -> Learn`

## Non-goals

Sprint 12 does not add:

- a browser extension;
- a general resume generator;
- autonomous job submission or outreach;
- a public portfolio hosting platform;
- server-side PDF generation;
- causal outcome analytics;
- an LLM dependency or API-key requirement.

## Product principles

- Package existing approved proof before recommending a new project.
- Use canonical Career Memory for factual claims.
- Preserve evidence IDs and source context.
- Keep outcome feedback separate from proof.
- Never invent metrics, tools, datasets, results, impact, or employer
  preferences.
- Make limitations and unsupported claims visible.
- Keep the primary artifact skimmable in under 60 seconds.
- Give the user final control over edits, readiness, and distribution.

## User flow

1. Career Diagnosis identifies a recognition gap and a proof-sprint objective.
2. The user chooses **Build this artifact**, or opens `/proof-artifacts`.
3. CareerOS prefills diagnosis context when available.
4. The user selects one approved memory, target role, artifact type, and target
   audience.
5. The builder retrieves the memory and its evidence trail.
6. The deterministic generator creates version 1 and saves it as `DRAFT`.
7. The user reviews the case study, evidence, warnings, readiness, and any
   outcome signals.
8. The user edits and saves, regenerates a new version, or changes lifecycle
   status.
9. The user copies a channel variant or opens the print-friendly view.
10. Later feedback remains a separate learning input and does not rewrite the
    source memory or historical artifact version.

## Inputs

Creation requires:

- `source_memory_id` for a user-owned canonical memory;
- a nonblank target role or program;
- an artifact type;
- a target audience.

It may also include `source_diagnosis_result_id`. A supplied diagnosis result
must belong to the current user and reference the selected memory in its
evidence map or proof sprint.

The generator may read approved `ARTIFACT_SUCCESS` feedback when the event is
captured by that diagnosis or directly linked to the selected memory.

## Approved-memory-only rule

The eligible-memory list is built from `canonical_memory_records`, which are
the durable projection of explicit approval decisions. Pending and rejected
review proposals must not appear and cannot be selected as proof.

The target role, diagnosis text, and user-facing edits do not become canonical
facts. Generation is a read-only consumer of Career Memory and evidence.

If the user has no approved memory, creation fails with:

> Approve career memories before building a proof artifact.

If a user selects an unavailable or another user's memory, the service returns
a scoped not-found response without disclosing the record.

## Artifact types

The persisted `artifact_type` enum supports:

| Value | Primary content |
| --- | --- |
| `CASE_STUDY` | Full one-page case study. |
| `GITHUB_README` | GitHub README outline. |
| `PORTFOLIO_PAGE` | Full case-study content for portfolio adaptation. |
| `APPLICATION_UPLOAD` | Full case-study content for an optional upload. |
| `OUTREACH_SUMMARY` | Short outreach blurb. |
| `INTERVIEW_STORY` | Evidence-backed interview answer. |
| `RESUME_BULLETS` | Resume bullet set. |

All types retain the complete structured case study and all supporting variants,
even when a shorter variant is the primary content.

## Target audiences

The `target_audience` enum supports:

- `APPLICATION_UPLOAD`
- `PORTFOLIO`
- `GITHUB`
- `OUTREACH`
- `INTERVIEW_PREP`
- `GENERAL`

Audience changes the `how_to_use` guidance. It does not change which facts are
approved.

## Case-study contract

`structured_sections` supports:

- `title`
- `target_claim`
- `role_relevance`
- `context`
- `problem`
- `data_or_inputs`
- `method`
- `evidence_used`
- `skills_demonstrated`
- `outcome_or_insight`
- `limitations`
- `what_this_proves`
- `how_to_use`
- `reviewer_question`
- `outcome_signals`
- `generator_version`

The rendered one-page content omits internal metadata but follows the same
section order.

For an analytics target and approved spectral/imaging evidence, the title may
be framed as:

> Data Analytics Case Study: Modeling Galaxy Morphology from Spectral and
> Imaging Data

The title exposes the transferable analytical work while the context section
retains the approved project identity. Domain terminology should be explained
or subordinated to the target-relevant claim.

## Generation rules

The provider-neutral service uses `local-deterministic-proof-v0` and requires no
LLM key. It combines approved structured fields with linked evidence excerpts
and source labels.

The generator should:

- identify only capabilities present in approved text or evidence;
- connect those capabilities to the target as framing, not as an employer fact;
- name data or inputs only when the source does;
- use a documented outcome only when Career Memory contains one;
- otherwise describe process and communication without implying business
  impact;
- preserve an explicit limitations section;
- generate supporting variants from the same claim and evidence.

For the approved Gas Kinematics example, role-relevant wording may include data
analysis, statistical modeling, uncertainty or error propagation,
visualization, and technical communication only when each is supported. The
builder must not add Python or another tool solely because the target is an
analytics role.

## Supporting variants

Every version contains:

- `resume_bullets` with two concise bullets;
- `cover_letter_paragraph`;
- `outreach_blurb`;
- `interview_answer`;
- `github_readme_outline`.

Variants must preserve the same limitations as the primary artifact. They are
not independent drafts and must not introduce new facts.

## Outcome signals versus proof

Outcome signals are approved user reports about artifact results. They may
inform presentation strategy, but they are not factual proof of a skill and do
not establish that a particular artifact caused an interview, callback, or
offer.

An event is eligible only when all of the following are true:

- status is `APPROVED`;
- event type is `ARTIFACT_SUCCESS`;
- it is present in the selected diagnosis snapshot or directly related to the
  source memory.

Archived and proposed events are excluded. Eligible signals are returned in
`outcome_signals`, and their IDs are stored separately in
`outcome_signal_ids`. Neither field contributes evidence IDs or readiness as
canonical proof.

Each signal includes a summary, guidance, and explicit causality caveat. Legacy
approved notes may be reparsed from `raw_note` when structured artifact fields
are absent.

## Warnings and unsupported claims

Every generated version warns against adding unapproved tools, datasets,
metrics, outcomes, or impact. Additional deterministic warnings appear when:

- the memory has no linked evidence IDs;
- no outcome is documented;
- no approved performance metric exists;
- an outcome signal is used;
- edited text adds a numeric claim absent from approved memory and evidence.

Warnings are part of the saved version and the API response. Readiness counts
only evidence records that resolve to the artifact owner; dangling or cross-user
IDs are retained for audit but cannot increase readiness or expose source text. Warnings remain
visible beside the preview; they are not hidden validation metadata.

Editing is allowed because the user owns the artifact. The system flags new
unsupported numeric claims rather than silently treating them as approved.

## Readiness

Each version stores a score in the inclusive range `0.0` to `1.0` plus a label:

| Score | Label | Meaning |
| --- | --- | --- |
| `< 0.40` | `NEEDS_EVIDENCE` | Useful partial structure, but evidence is too thin to share. |
| `0.40-0.59` | `DRAFTABLE` | Enough support to draft; material review or evidence work remains. |
| `0.60-0.79` | `STRONG_DRAFT` | Substantial supported content with visible limitations. |
| `>= 0.80` | `READY_TO_SHARE` | Strong deterministic readiness signal; user review is still required. |

The score considers:

- whether approved memory exists;
- linked evidence count;
- target claim clarity;
- method/context detail;
- role-relevant supported capabilities;
- whether an outcome is documented.

No evidence caps readiness below `DRAFTABLE`. A missing documented outcome caps
generated readiness below `READY_TO_SHARE`. Unsupported numeric edits cap the
version at `DRAFTABLE` and add a verification warning.

Readiness is not hiring likelihood and does not automatically change artifact
status.

## Persistence

### `proof_artifacts`

The artifact record stores:

- `id`, `user_id`, and title;
- artifact type;
- target role and audience;
- required source memory ID;
- optional source diagnosis result ID;
- status;
- created and updated timestamps.

Status values are:

- `DRAFT`
- `REVIEWED`
- `READY`
- `ARCHIVED`

### `proof_artifact_versions`

The version record stores:

- `id`, `user_id`, and artifact ID;
- version number unique within the artifact;
- title, claim, primary content, and structured sections;
- evidence IDs and outcome-signal IDs;
- warnings;
- readiness score and label;
- supporting variants;
- created and updated timestamps.

Create writes version 1. Regeneration locks the artifact, computes the next
version number, saves a new version, and resets status to `DRAFT`. A target-role
change clears the previous diagnosis-result link. Direct edit updates only the
latest version in place, synchronizes title/claim representations, and reruns
unsupported-number checks across the complete saved version.

Historical snapshots remain readable when their source proposal later leaves the
approved state, but they cannot be regenerated until that source is approved
again.

The API response contains the latest version and `version_count`; a complete
version-history reader is outside v0.

## API contract

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/api/proof-artifacts/eligible-memories` | Return user-owned approved memory options with evidence counts, IDs, source labels, and confidence. |
| `POST` | `/api/proof-artifacts` | Generate an artifact and save version 1. Returns `201`. |
| `GET` | `/api/proof-artifacts` | List saved artifacts ordered by most recently updated. |
| `GET` | `/api/proof-artifacts/{id}` | Return one artifact's metadata and latest version. |
| `POST` | `/api/proof-artifacts/{id}/regenerate` | Optionally change target role, audience, or type and append a generated version. |
| `PATCH` | `/api/proof-artifacts/{id}` | Update title or lifecycle status. A changed target role or audience is rejected with guidance to regenerate. |
| `PATCH` | `/api/proof-artifacts/{id}/versions/{version_id}` | Update title, claim, content, structured sections, or supporting variants. |

Response provenance includes:

- source memory title and ID;
- optional source diagnosis result ID;
- evidence IDs plus evidence reference labels/excerpts;
- outcome signals and IDs;
- warnings and readiness;
- latest version and total version count.

`404` is used for unavailable user-scoped resources. `422` is used for invalid
source relationships, missing approved memory, and unsupported request state.

## Frontend behavior

The `/proof-artifacts` workspace includes:

### Input

- approved-memory selector;
- target role/program input;
- artifact type selector;
- target audience selector;
- generate action;
- a clear approved-memory empty state.

### Output

- primary artifact preview;
- structured sections;
- evidence IDs, source labels, and excerpts;
- warnings and unsupported-claim guidance;
- readiness score and label;
- outcome signals in a section labeled as strategy signals, not proof;
- supporting channel variants.

### Controls

- edit and save;
- regenerate;
- mark reviewed or ready;
- archive;
- copy primary text;
- copy resume bullets and outreach text;
- open a print-friendly view.

The diagnosis workspace may link directly into the builder and prefill the
target, suggested source memory, and diagnosis result. Navigation and dashboard
actions expose the builder independently as well.

## Print and copy behavior

Copy actions use the text already returned for the latest saved version. They do
not regenerate content or call an external model.

The print-friendly view should:

- show the current primary artifact and essential provenance;
- remove application navigation and edit controls from print output;
- remain readable on a standard page;
- allow the browser to print or save as PDF.

Native PDF generation and branded export templates are deferred.

## Acceptance criteria

Sprint 12 is complete when:

- a user can generate a saved artifact from approved memory without an LLM key;
- unapproved or another user's memory cannot be used;
- evidence IDs and source labels remain inspectable;
- the case study contains a clear claim and target relevance;
- unsupported outcome/metric warnings are visible;
- readiness is deterministic and visible;
- approved outcome signals remain separate from proof;
- regeneration appends a version;
- edited content can be saved;
- lifecycle status persists;
- the workspace provides useful copy and print behavior;
- diagnosis, dashboard, and navigation can reach the builder.

## Limitations

- Templates are deterministic and intentionally narrow.
- v0 generates text, not a designed portfolio site.
- Browser print/save-as-PDF is the only PDF workflow.
- Full visual version history is not exposed.
- Readiness does not predict evaluator response.
- Sparse or vague approved memory produces a partial artifact.
- Outcome feedback remains observational and may be biased or incomplete.

## Future follow-ups

- Full version history and side-by-side comparison.
- Selective evidence inclusion and richer provenance views.
- Reviewer comments and review requests.
- Accessible branded PDF and document exports.
- Portfolio and GitHub publishing integrations.
- Multiple template families and visual layouts.
- Outcome-linked analysis of which artifact framing works for which targets.
- Privacy-aware export, deletion, and portability controls.
