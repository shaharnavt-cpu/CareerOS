# Application Package Builder

## Status

Sprint 14, 14.1, 14.1.1, and 14.1.2 implementation guide. The builder is
available through the `/application-packages` workspace and the
`/api/application-packages` API.

CareerOS does not generate application text from an unconstrained prompt. It
builds a reviewable package from exact, user-selected approved Career Memory and
preserves the inputs, provenance, warnings, and edits used for each version.

## What Sprint 14 added

An application package contains:

- a positioning summary with recommended emphasis, risks, and a do-not-claim
  list;
- role-tailored resume bullet groups;
- a structured cover-letter draft with paragraph-level traces;
- application answers matched to explicitly supplied questions;
- ready proof artifacts to attach, draft artifacts to finish reviewing, or proof
  artifacts worth building;
- reviewer questions, unsupported-claim warnings, and a human-readable evidence
  trace; and
- an immutable history of generated, regenerated, and user-edited versions.

The package workspace stores target details separately from generated versions.
The target can include a linked opportunity plus role title, company, location,
job type, description, required/preferred skills, responsibilities, an ordered
application-question list, and explicit approved-memory selections.

## Generation path

```text
Target context (relevance only)
  + explicit ordered application questions
  + exact selected approved memory IDs
  -> compile each memory independently
  -> rank approved profiles for the target
  -> build immutable evidence atoms
  -> compose structured candidate claims and analysis
  -> sanitize narrowly and validate candidate claims
  -> audit requirements and assemble claim/evidence traces
  -> save an immutable package version
```

Local generation is deterministic and does not require an OpenAI or Anthropic
key. An optional OpenAI provider receives the same bounded writing input and is
subject to the same deterministic validation before persistence. The provider,
model, and generator version are stored safely with saved versions. Role text
can change ranking and wording, but it cannot add a fact to a compiled profile.

The current pipeline recommends and selects 2-4 ranked memories by default,
while preserving manual additions, removals, and order. It returns concise
resume groups, a natural cover letter, direct answers for the supplied
application questions, proof suggestions, and reviewer questions.

### Writing providers and deterministic validation

The provider seam sits between compiled/ranked evidence and immutable version
persistence. `local-deterministic` is the key-free default. `openai` uses one
strict structured Responses API request with `store=false`; its default writer
is `gpt-5.6-terra`. An optional `gpt-5.6-sol` recruiter review/rewrite is
disabled by default and cannot add evidence or claims. The interface is neutral
enough to add another provider, including Anthropic, without rewriting package
truth and persistence logic.

Both paths perform semantic job understanding, memory ranking, claim planning,
drafting, recruiter critique, and quality evaluation. Broad requirements such
as analytics, reporting, modeling, communication, and data quality can match
equivalent approved proof. Concrete tools still require direct proof.
CareerOS then validates factual claims, tools, metrics, cross-memory boundaries,
strategy-only labels, evidence references, and excluded records before saving.
Provider errors do not erase existing output or create empty versions.

### Sprint 14.1.1 claim contract and persistence gate

The provider no longer relies on free-text evidence labels as its primary claim
contract. CareerOS supplies immutable evidence atoms with stable atom/approved-
claim IDs, canonical-memory ownership, optional enrichment and proof-artifact
IDs, direct source references, factual text, supported tools/methods, structured
outcome support, allowed certainty, support type, and prohibited expansions.
Each candidate-facing positioning, resume, cover-letter, or application-answer
field must return an exact claim record with its evidence-atom IDs, type, tools,
outcome, and certainty.

Analysis fields remain separate: job understanding, requirement coverage,
unsupported requirements, missing-proof/do-not-claim guidance, reviewer
questions, proof suggestions, target-job tool lists, and quality/critic/
validation notes do not become applicant claims merely because they mention a
tool or outcome. AWS or Kubernetes may therefore appear as an unsupported gap,
while the same term is blocked as candidate experience unless a cited direct
atom explicitly supports it.

Outcome validation compares structured source, action, object, result,
qualifier, certainty, metric, and project ownership. It permits harmless
paraphrasing but blocks material object/result changes, metric invention,
certainty inflation, reference drift, and cross-memory transfer. Before a
version is saved, a narrow sanitizer may remove only a separable optional
unsupported-warning sentence. The repair is recorded in validation metadata;
central factual claims are never silently rewritten, and an unsafe draft
creates no new version.

Safe failure diagnostics contain only a stable code, section, field path,
normalized disputed phrase, evidence IDs, expected evidence category, and the
`user-facing`/`analysis-only` classification. Prompts, private career context,
full responses, credentials, headers, and hidden reasoning are excluded.

### Sprint 14.1.2 application question/answer contract

Application questions are persisted on the package and passed explicitly to
both providers. Each ordered question supplies `question_id`, `question_text`,
`required`, optional `maximum_length`, optional `response_type`, and
`relevant_target_requirement_ids` where applicable. The provider must not infer
how many answers exist or manufacture generic prompts to satisfy a fixed count.

Each returned application answer includes `question_id`, answer text,
`evidence_reference_ids`, `evidence_atom_ids`, `tools_claimed`,
`outcome_claimed`, `certainty`, and `validation_metadata`. Exactly one non-empty
answer is required for each required question. Unknown or duplicate IDs are
invalid, answers preserve supplied question order, optional unanswered
questions may be omitted, and zero supplied questions requires zero snippets.
The structural validation codes are
`MISSING_REQUIRED_APPLICATION_ANSWER`, `DUPLICATE_APPLICATION_ANSWER`,
`UNKNOWN_APPLICATION_QUESTION_ID`, `EMPTY_APPLICATION_ANSWER`, and
`APPLICATION_ANSWER_ORDER_MISMATCH`.

A missing required answer is eligible for the single structured repair budget.
The repair input is restricted to missing question IDs/text, already valid
package sections, relevant evidence atoms, prohibited claims, and the strict
answer schema. The service merges only repaired answers and validates the whole
package again; it does not regenerate a valid resume or cover letter. A failed
repair creates no version and preserves the prior immutable output. Repaired
answers remain candidate-facing claims, so unsupported tools/outcomes and
missing or invalid evidence references are still rejected. Sprint 14.1.1 claim
validation and the `private`/`demo-shared` data policy are unchanged.

## Trust boundaries

The current user and the exact selected `memory_id` values define the package's
factual boundary.

- Only approved canonical memory and approved enrichment linked to that exact
  memory can support factual text.
- Proposed, rejected, archived, foreign, or mismatched enrichment is excluded
  by the Career Memory Compiler.
- Target text is stored as `TARGET_CONTEXT` with `RELEVANCE_ONLY` support. It
  can choose emphasis but is not proof.
- Approved outcome feedback is stored as a `STRATEGY_SIGNAL` with
  `STRATEGY_ONLY` support. It can guide framing but cannot prove a skill or
  causal outcome.
- Missing target requirements become warnings, unsupported claims, and reviewer
  questions instead of invented experience.
- Generated prose never updates canonical memory.

Gas Kinematics and UNICORN remain the boundary regression pair. Gas may use
only its approved spectroscopy, modeling, morphology, and uncertainty evidence;
UNICORN may use only its approved inspection, categorization, t-SNE, and
data-quality evidence. Similar titles or role relevance never permit evidence
to cross memory IDs.

## Evidence trace and claim ledger

Evidence traces are readable records rather than bare IDs. Each record carries
a source label, supporting detail, source type, support type, applicable memory
and enrichment/evidence IDs, and a caveat where needed.

| Source type | Support type | Meaning |
| --- | --- | --- |
| `APPROVED_MEMORY` | `DIRECT` | Approved canonical memory or its eligible linked evidence supports the statement. |
| `APPROVED_ENRICHMENT` | `DIRECT` | Approved detail attached to the same selected memory supports the statement. |
| `APPROVED_MEMORY` | `INFERRED_FRAMING` | Role-aware wording is derived from direct approved proof without introducing a fact. |
| `STRATEGY_SIGNAL` | `STRATEGY_ONLY` | Approved outcome feedback may guide emphasis but is not factual proof. |
| `TARGET_CONTEXT` | `RELEVANCE_ONLY` | The posting or target settings explain relevance only. |

Resume bullets include direct and inferred-framing traces, a confidence value,
warnings, and a plain-language reason for their selection. Cover-letter
paragraphs and application snippets carry their own traces. The aggregate
package trace preserves all eligible proof, strategy signals, and target
context used by the version. Claim traces retain all approved direct sources
from the applicable compiled profile rather than truncating the source list.

Each generated version stores a claim ledger for the positioning summary,
resume bullets, cover-letter paragraphs, and snippets. Ledger entries record
the surface text, factual memory/evidence/enrichment references, support level,
warnings, strategy-signal references, and whether the surface was user-edited.
An exact changed claim is rebuilt as `user_review_required`; its factual and
strategy IDs are cleared because preserved traces are review context, not
certification of new wording. Unchanged claims keep their original ledger
support.

## Warnings and edits

The deterministic audit recognizes a bounded set of common requirements,
including data analysis, modeling, data quality, cloud platforms, Kubernetes,
automation, machine learning, and production ML deployment. It matches against
positive capability fields, excludes limitations and negated clauses, and uses
token boundaries for custom skills. A requested item absent from the eligible
compiled capabilities produces a visible `UNSUPPORTED_TARGET_REQUIREMENT`
warning. The package also surfaces compiler claim boundaries, missing
quantified outcomes, and the non-proof status of outcome signals. Sparse memory
produces explicit gap language rather than an invented capability summary.

Saving edited outputs appends a `USER_EDIT` version; it never changes a prior
version or canonical memory. Nested output objects remain accepted for API
compatibility, but the service merges only allowed applicant-authored text.
Memory/evidence/enrichment IDs, traces, confidence, claim metadata,
proof-artifact identities, and other provenance stay server-owned.

Only the exact changed claims are marked edited. Their ledger entries are
rebuilt from the new text as `user_review_required`, without factual IDs.
The audit compares changed factual sentences with the most recent generated or
regenerated baseline, so unchanged job-target wording is not reclassified as an
applicant claim across later edit versions. New unsupported plain, percentage,
comma-formatted, magnitude, and ratio numbers produce a blocking
`UNSUPPORTED_EDITED_NUMBER` warning; numeric target phrases are ignored only in
explicit non-claim target context, including a named target skill discussed as
an interest rather than as experience. Recognized unsupported capability
wording in a resume bullet, or a first-person/fit capability claim elsewhere,
produces `UNSUPPORTED_EDITED_CLAIM`. Resume edits are audited against that
group's exact memory; borrowing a distinctive fact from another selected memory
produces `CROSS_MEMORY_EDITED_CLAIM`. Audit warnings and unsupported-claim
entries are recomputed on each saved edit, so correcting the text clears
obsolete edit findings. Sparse/title-only records cannot earn project-specific
ranking or reviewer shortcuts, and vague problem text alone cannot become an
action resume bullet. Human review remains the final gate.

## Persistence and freshness

Migration `20260715_0011` adds two tables:

- `application_packages` is the mutable, user-owned workspace and target
  selection. Its status is `DRAFT`, `READY`, or `ARCHIVED`.
- `application_package_versions` is the append-only snapshot history. It stores
  the target and compiled-profile snapshots, selected memories, generated
  outputs, evidence trace, warnings, claim ledger, IDs used, edits, generator
  version, fingerprint, reason, and timestamp.

Sprint 14.1 migration `20260717_0012` adds JSON-backed writing-intelligence,
quality-review, safe provider-metadata, and validation-summary fields. Sprint
14.1.1 reuses that boundary; it adds no migration and leaves `20260717_0012`
unchanged. Sprint 14.1.2 migration `20260721_0013` adds the ordered
`application_questions` JSONB input to the mutable package workspace.

Generation reasons are `GENERATED`, `REGENERATED`, and `USER_EDIT`. Every
generation, regeneration, or saved edit creates the next version number and
returns the package to `DRAFT` for review.

The input fingerprint covers the target snapshot, ordered application questions,
selected memory IDs, and the current compiled-profile snapshots. If target
settings, questions, selections, or approved proof change, the package reports
`is_stale`. A stale package cannot be marked
`READY`, is exposed as `DRAFT` even if approved proof changed after readiness,
and cannot accept edited outputs until it is regenerated. Target-input changes
also demote a stored ready package when they make its version stale. A current
version with any `BLOCKING` warning cannot be marked `READY`. Historical
versions remain available and unchanged. Archived packages are omitted from
the default list unless `include_archived=true` is requested.

## API

All endpoints are under `/api/application-packages`:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/eligible-memories?target_role=...` | List current-user approved memory options, optionally ranked for a role. |
| `POST` | `/` | Create a draft package and validate any selected memories/opportunity. |
| `GET` | `/?include_archived=false` | List packages; archived packages are hidden by default. |
| `GET` | `/{package_id}` | Read a package, its flattened latest output, and complete version history. |
| `POST` | `/{package_id}/generate` | Generate the first version or append a regenerated version. |
| `POST` | `/{package_id}/regenerate` | Append a regenerated version after an initial version exists. |
| `PATCH` | `/{package_id}` | Update target fields, selected memories, or package status. |
| `PATCH` | `/{package_id}/outputs` | Merge reviewed output edits into a new immutable `USER_EDIT` version. |

The detail response exposes the positioning summary, bullet groups, letter,
snippets, proof suggestions, evidence trace, warnings, reviewer questions,
unsupported claims, source IDs used, `is_stale`, latest version, and all saved
versions.

## Workspace behavior

The Application Packages navigation item opens `/application-packages`. The
workspace can link a saved Application Intelligence opportunity or accept the
target manually. Its approved-memory panel shows role-ranked recommendations,
but only checked memory IDs are used; the user can reorder that explicit
selection before generation. Saved packages can be reopened, and archived
packages appear only when the user enables the archived view.

The review surface provides:

- separate recommended and selected memories, with 2-4 recommendations selected
  by default unless the user has saved a manual selection;
- grouped requirement coverage, warnings, and deduplicated evidence traces by
  canonical memory;
- a concise writing-quality review and discreet provider/model label;
- editable primary/strongest positioning text, resume-bullet text, full
  cover-letter text, and each supplied-question answer;
- copy controls for individual sections, the full package, and historical
  versions;
- bullet/snippet evidence details and paragraph-level cover-letter traces;
- visible warnings, unsupported claims, do-not-claim guidance, and strategy
  notes;
- links to open an existing proof artifact or start building a missing one;
- reviewer questions and expandable version history; and
- regenerate, save edits, mark ready, archive, and restore-draft actions.

The interface treats generated content as a draft. Target or memory changes
hide the current output behind a visible stale/new-draft panel rather than
relabeling it for new inputs. The saved snapshot remains in history, and the
user can open it only through a read-only "Historical snapshot only — not
current output" expander, copy it as historical text, restore its inputs, or
generate a new version. Backend freshness checks also require regeneration
before readiness or edited-output saving. Unsaved manual edits disable
target, opportunity, memory, package-switch, generation, copying, and status
actions in the UI until they are saved or undone. During a request, the input
and review surfaces are locked to prevent a late response from overwriting a
different package. Saved user-edited claims read the server claim ledger and
show `User review required`; their preserved traces are labeled as reference
context rather than claim-level validation. Warnings and evidence remain
first-class review surfaces, not hidden metadata.

## Current limits

- Local requirement interpretation remains intentionally bounded; the OpenAI
  path adds semantic interpretation but cannot override factual validation.
- The package does not overwrite a base resume or submit an application.
- Copy controls are the practical output path; PDF/DOCX layout and ATS
  guarantees are not part of Sprint 14.
- Only a `READY` proof artifact is suggested as `ATTACH`. A non-archived draft
  or reviewed artifact is `REVIEW`; absence produces `BUILD`. Artifact
  content and Career Diagnosis are not silently treated as factual sources.
- Package-version-linked outcome tracking belongs to the later application
  tracker; existing outcome signals remain compiler-bounded strategy context.
- Sprint 14.1.1 non-live backend and frontend verification is complete. Sprint
  14.1.2 made no live provider request; OpenAI acceptance remains separately
  gated by `RUN_LIVE_OPENAI_TESTS=true` and explicit user approval.

## MVP impact

Sprint 14 closes the central personal-MVP gap: a user can move from approved
professional memory and a real target job to a saved, reviewable resume/cover-
letter package without starting from a blank page or hiding provenance. Guided
gap interviewing, richer export, seeded demo data, and end-to-end application
tracking remain follow-up work.
