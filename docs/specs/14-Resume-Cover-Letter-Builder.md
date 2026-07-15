# Sprint 14: Resume and Cover Letter Builder

**Status:** implemented.
**Product surface:** Application Package Builder.
**Route:** `/application-packages`.
**Migration:** `20260715_0011`.
**Depends on:** approved Canonical Career Memory, approved Project Evidence
Enrichment, Career Memory Compiler, Proof Artifact Builder, and Application
Intelligence opportunity records.

For the implementation and operating guide, see
[28-Application-Package-Builder.md](../28-Application-Package-Builder.md).

## 1. Product outcome

Sprint 14 turns approved professional memory into a target-specific,
reviewable, and versioned application package. One package can contain:

- a positioning summary;
- tailored resume bullets grouped by approved memory;
- a cover-letter draft;
- five common application-answer snippets;
- suggested proof artifacts;
- evidence traces, a claim ledger, warnings, unsupported claims, and reviewer
  questions; and
- immutable generated, regenerated, and user-edited versions.

The builder is not a generic resume bot. It selects and reframes approved proof
for a role; it does not create proof, overwrite a base resume, or hide missing
support behind polished prose.

## 2. Implemented user story

A user can create or reopen a package, enter a role and job context, select
approved memories, generate deterministic application materials, inspect the
support and gaps, copy the useful text, save reviewed edits as another version,
regenerate after inputs change, and mark the package draft, ready, or archived.

Target input supports:

- optional linked application-opportunity ID;
- role title, company, location, and job type;
- job/role description;
- required and preferred skill lists;
- responsibility list; and
- up to 50 unique selected approved-memory IDs.

Package lists exclude archived packages by default. An archived package remains
retrievable and can be included explicitly in list requests.

## 3. Factual and strategy boundaries

The factual input set is:

```text
current user
  + exact selected approved canonical memory IDs
  + approved enrichment linked to each exact memory
  + eligible linked evidence
  -> independently compiled memory profiles
  -> generated package version
```

The following contracts are enforced:

1. Every selected memory is compiled through the Career Memory Compiler.
2. Proposed, rejected, archived, foreign, and wrong-memory enrichment cannot
   support package text.
3. The selected memory ID is authoritative. Similar names never permit one
   project's evidence to be borrowed by another.
4. Target job text influences ranking, emphasis, and gap detection only. It is
   stored as relevance context, not factual proof.
5. Approved outcome feedback remains a strategy-only signal. Archived outcome
   feedback is excluded by the compiler.
6. Missing methods, tools, deployment, leadership, metrics, or results become
   warnings/questions; they are not filled in with plausible language.
7. Generated output and user edits never update canonical memory.

### Regression-critical examples

- Gas Kinematics may use only approved Gas evidence such as spectroscopy,
  H-alpha/Gaussian analysis, GALFIT/morphology, validation, and uncertainty.
- UNICORN may use only approved UNICORN evidence such as image/detection
  inspection, categorization, t-SNE, data quality, and human review.
- A cloud or production-ML posting can surface AWS, Kubernetes, cloud, and
  deployment gaps, but cannot cause those terms to appear as user experience.

## 4. Deterministic generation contract

The service uses generator version
`local-deterministic-application-package-v1`. No provider key is required.

For a generation request it:

1. validates package ownership, optional opportunity ownership, and selected
   memory eligibility;
2. compiles each selected memory independently for the target role;
3. ranks compiled profiles by bounded target overlap, compiler confidence, and
   conservative Gas/UNICORN role bonuses;
4. composes structured outputs from supported compiled fields;
5. checks a bounded vocabulary of target requirements against positive
   capability fields, excluding limitations and negated clauses;
6. builds human-readable traces and a per-surface claim ledger; and
7. appends an immutable version with input/provenance snapshots.

Current output bounds are intentionally small: up to four resume groups with up
to two bullets each, two proof stories in the cover letter, five snippets, three
proof-artifact suggestions, and five reviewer questions.

### Resume bullets

Each group names a section suggestion, memory ID/title, and target reason. Each
bullet contains its text, direct proof plus an inferred-framing trace, compiler
confidence, warning list, and selection rationale. All approved direct sources
for that profile remain in the trace. If approved findings contain no supported
quantity, the bullet is labeled: "No quantified outcome is currently supported
for this claim." Sparse profiles receive explicit gap wording rather than an
invented technical capability.

### Cover letter

The letter has a heading, greeting, opening, body paragraphs, closing, and full
text. Opening and closing target references use relevance-only context;
substantive project paragraphs carry direct and inferred-framing traces to
their selected profiles. Outcome feedback, when present, appears only in
`strategy_notes` with its non-proof caveat.

### Positioning, snippets, and proof artifacts

The positioning summary identifies primary/secondary proof, risks, recommended
emphasis, and a do-not-claim list. The five snippets answer interest, fit,
project, challenge, and technical-skills prompts and retain their own traces and
warnings.

Proof Artifact Builder records are not imported as new factual evidence. A
`READY` artifact is suggested as `ATTACH`; a non-archived draft or reviewed
artifact is `REVIEW`; and absence produces a `BUILD` suggestion.

## 5. Evidence and warning contracts

Evidence source and support types remain separate:

| Source type | Support type | Allowed use |
| --- | --- | --- |
| `APPROVED_MEMORY` | `DIRECT` | Factual support from the selected memory and eligible evidence. |
| `APPROVED_ENRICHMENT` | `DIRECT` | Factual support from approved detail on that same memory. |
| `APPROVED_MEMORY` | `INFERRED_FRAMING` | Role-aware wording derived from direct approved proof without adding a fact. |
| `STRATEGY_SIGNAL` | `STRATEGY_ONLY` | Framing guidance only; never skill or causality proof. |
| `TARGET_CONTEXT` | `RELEVANCE_ONLY` | Role relevance and emphasis only. |

Claim-ledger entries cover the positioning summary, resume bullets,
cover-letter paragraphs, and snippets. They preserve text, memory/evidence/
enrichment references, support level, warnings, strategy-signal references,
and user-edit state.

The audit produces structured `INFO`, `CAUTION`, or `BLOCKING` warnings. Current
warning classes cover unsupported target requirements, absent quantified
outcomes, compiler claim boundaries, strategy signals, user-edit review,
numbers introduced without approved support, and recognized unsupported
first-person tool, skill, or deployment claims.

Nested output objects remain accepted for compatibility, but edits can change
only approved text surfaces: primary/strongest positioning, generated bullet
text, full cover-letter text, snippet text, and reviewer questions. Provenance,
IDs, traces, confidence, claim metadata, and proof-artifact identities remain
server-owned.

Saving rebuilds only the exact changed claim entries. They are marked
`user_review_required`, have factual/strategy IDs cleared, and state that the
preserved trace is reference context rather than certification. The audit is
per-memory for resume bullets, detects unsupported numbers and recognized tool/
skill/deployment claims, detects distinctive cross-memory borrowing, excludes
negated/limitation text from support, and uses token-bound custom skills. It
compares changed factual sentences against the latest generated/regenerated
baseline, detects plain, percentage, comma-formatted, magnitude, and ratio
numbers, and ignores numeric target identifiers only where they remain explicit
non-claim target context (for example, a role identifier or a target skill the
applicant wants to learn about). It recomputes edit findings so a corrected later version
clears obsolete blocking warnings and unsupported claims. Project-specific
ranking/reviewer shortcuts require compiled capability evidence, and vague
problem text alone does not become an action bullet.

## 6. Persistence and versioning

`application_packages` stores the mutable workspace:

- owner and optional opportunity link;
- display name and target fields;
- required/preferred skills and responsibilities;
- selected memory IDs;
- `DRAFT`, `READY`, or `ARCHIVED` status; and
- created/updated timestamps.

`application_package_versions` stores append-only snapshots:

- ordered version number and generation reason;
- target, selected-memory, and compiled-profile snapshots;
- SHA-256 input fingerprint;
- structured outputs, aggregate evidence trace, warnings, and claim ledger;
- memory, enrichment, and outcome-signal IDs used;
- user-edit metadata and generator version; and
- creation timestamp.

The generation reason is `GENERATED`, `REGENERATED`, or `USER_EDIT`. Generate,
regenerate, and output-edit operations append a version and return the package
to `DRAFT`. Earlier versions are never updated in place.

The fingerprint includes the current target snapshot, selected-memory IDs, and
compiled-profile snapshots. A mismatch sets `is_stale`. Stale output cannot be
marked `READY` or saved as a new edited version; the user must regenerate. A
ready package is returned as `DRAFT` whenever current approved proof makes it
stale, including proof changes after review. A latest version containing any
`BLOCKING` warning also cannot be marked `READY`.

## 7. Implemented API

All routes are prefixed by `/api/application-packages`.

| Method | Path | Contract |
| --- | --- | --- |
| `GET` | `/eligible-memories` | Approved memory options; optional `target_role` ranking. |
| `POST` | `/` | Create a draft package. |
| `GET` | `/` | List packages; optional `include_archived`. |
| `GET` | `/{package_id}` | Return package details, latest flattened output, and all versions. |
| `POST` | `/{package_id}/generate` | Create the first version, or a regenerated version if one exists. |
| `POST` | `/{package_id}/regenerate` | Require an existing version and append a regenerated one. |
| `PATCH` | `/{package_id}` | Update target, selection, opportunity, or status. |
| `PATCH` | `/{package_id}/outputs` | Merge allowed text edits, preserve server-owned provenance, and append a `USER_EDIT` version. |

Ownership failures are hidden behind package-not-found or validation responses.
Invalid generation/edit/readiness transitions return `422`; unknown or foreign
packages return `404`.

## 8. Implemented workspace contract

The `/application-packages` page is a review workspace, not a chat surface. It
supports manual target entry or a linked saved Application Intelligence
opportunity. It shows role-ranked approved-memory recommendations while keeping
selection and ordering explicit, and it can create/reopen packages, include
archived packages on request, generate/regenerate, save edits, and change
draft/ready/archive status.

Editable UI fields are the primary and strongest positioning text, each resume
bullet, the full cover letter, and each of the five snippets. Copy controls exist
for individual outputs, the assembled package, and historical versions. The
workspace also shows bullet/snippet traces, paragraph-level letter traces,
warnings, unsupported/do-not-claim items, strategy notes, proof-artifact links,
reviewer questions, and expandable history.

The UI must keep these trust cues visible:

- generated material is a draft until the user reviews it;
- the selected memory/project is named on proof-bearing output;
- target or selection changes hide existing output behind a stale/new-draft
  panel; the saved version is available only in a clearly labeled, read-only
  historical expander with copy access;
- stale output requires regeneration before readiness or edit saving;
- warnings and unsupported claims remain visible without hover; and
- proof, strategy-only signals, and target-only context are labeled separately.

Unsaved edits lock target/opportunity/memory changes, package switching,
generation, copying, and status changes in the UI. Busy requests also lock the
input/review surfaces. Saved edited claims consume claim-ledger review status
and relabel preserved traces as reference context rather than direct validation.
Saving appends a `USER_EDIT` version; it does not mutate the displayed
historical version or Career Memory.

## 9. Acceptance boundaries

Sprint 14's implementation is complete only while these regressions stay true:

- create/list/detail/update/generate/regenerate/output-edit flows preserve user
  ownership and version history;
- only exact selected approved memory and approved same-memory enrichment feed
  factual output;
- Gas and UNICORN detail never crosses project boundaries;
- outcome feedback is strategy-only and archived signals are excluded;
- target requirements can produce relevance or warnings but not experience;
- resume bullets, letter paragraphs, and snippets retain evidence traces;
- target, selection, or compiled-proof changes are detected as stale;
- regeneration does not mutate approved memory;
- unsupported edited numbers and recognized tool, skill, or deployment claims
  receive blocking warnings;
- cross-memory resume edits are detected against the exact group memory;
- corrected edits clear obsolete audit findings;
- blocking warnings prevent `READY`; and
- archived packages are hidden from the default list.

## 10. Deferred work

- PDF/DOCX and visual resume templates;
- ATS scoring or guarantees;
- open-ended company research;
- browser extraction, autofill, and automatic submission;
- broader semantic auditing beyond the implemented saved-edit claim rules;
- guided collection of missing proof;
- package-version-linked application events and outcome tracking;
- production authentication/multi-user hardening; and
- public portfolio or hosted document publishing.
