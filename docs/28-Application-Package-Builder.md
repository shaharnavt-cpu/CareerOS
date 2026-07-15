# Application Package Builder

## Status

Sprint 14 implementation guide. The builder is available through the
`/application-packages` workspace and the `/api/application-packages` API.

CareerOS does not generate application text from an unconstrained prompt. It
builds a reviewable package from exact, user-selected approved Career Memory and
preserves the inputs, provenance, warnings, and edits used for each version.

## What Sprint 14 added

An application package contains:

- a positioning summary with recommended emphasis, risks, and a do-not-claim
  list;
- role-tailored resume bullet groups;
- a structured cover-letter draft with paragraph-level traces;
- five common application-answer snippets;
- ready proof artifacts to attach, draft artifacts to finish reviewing, or proof
  artifacts worth building;
- reviewer questions, unsupported-claim warnings, and a human-readable evidence
  trace; and
- an immutable history of generated, regenerated, and user-edited versions.

The package workspace stores target details separately from generated versions.
The target can include a linked opportunity plus role title, company, location,
job type, description, required/preferred skills, responsibilities, and explicit
approved-memory selections.

## Generation path

```text
Target context (relevance only)
  + exact selected approved memory IDs
  -> compile each memory independently
  -> rank approved profiles for the target
  -> compose positioning, bullets, letter, snippets, and proof suggestions
  -> audit requirements and assemble claim/evidence traces
  -> save an immutable package version
```

Generation is deterministic and does not require an OpenAI or Anthropic key.
The generator version is stored with every saved version. Role text can change
ranking and wording, but it cannot add a fact to a compiled profile.

The current composer uses up to four ranked memories for resume groups, the two
strongest profiles for the cover letter, and the three strongest profiles for
proof-artifact suggestions. It returns five copy-ready snippets and up to five
reviewer questions.

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

Generation reasons are `GENERATED`, `REGENERATED`, and `USER_EDIT`. Every
generation, regeneration, or saved edit creates the next version number and
returns the package to `DRAFT` for review.

The input fingerprint covers the target snapshot, selected memory IDs, and the
current compiled-profile snapshots. If target settings, selections, or approved
proof change, the package reports `is_stale`. A stale package cannot be marked
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

- editable primary/strongest positioning text, resume-bullet text, full
  cover-letter text, and five answer snippets;
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

- Requirement detection and prose composition use bounded deterministic
  heuristics, not open-ended job-posting interpretation.
- The package does not overwrite a base resume or submit an application.
- Copy controls are the practical output path; PDF/DOCX layout and ATS
  guarantees are not part of Sprint 14.
- Only a `READY` proof artifact is suggested as `ATTACH`. A non-archived draft
  or reviewed artifact is `REVIEW`; absence produces `BUILD`. Artifact
  content and Career Diagnosis are not silently treated as factual sources.
- Package-version-linked outcome tracking belongs to the later application
  tracker; existing outcome signals remain compiler-bounded strategy context.

## MVP impact

Sprint 14 closes the central personal-MVP gap: a user can move from approved
professional memory and a real target job to a saved, reviewable resume/cover-
letter package without starting from a blank page or hiding provenance. Guided
gap interviewing, richer export, seeded demo data, and end-to-end application
tracking remain follow-up work.
