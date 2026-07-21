# Sprint 14: Resume and Cover Letter Builder

**Status:** Sprint 14 implemented; Sprint 14.1 provider/intelligence extension,
Sprint 14.1.1 claim-contract hardening, and Sprint 14.1.2 application-question/
answer alignment are in the current working tree. Live OpenAI acceptance remains
pending.
**Product surface:** Application Package Builder.
**Route:** `/application-packages`.
**Migrations:** `20260715_0011`, `20260717_0012`, `20260721_0013`.
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
- answers for explicitly supplied application questions;
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
- responsibility list;
- up to 50 ordered structured application questions; and
- up to 50 unique selected approved-memory IDs.

Package lists exclude archived packages by default. An archived package remains
retrievable and can be included explicitly in list requests.

## 3. Factual and strategy boundaries

The factual input set is:

```text
current user
  + explicit application questions (target context only)
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
to two bullets each, two proof stories in the cover letter, one answer for each
supplied required application question, three proof-artifact suggestions, and
five reviewer questions. Optional unanswered questions may be omitted, and an
empty question list produces no snippets.

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

### Positioning, application answers, and proof artifacts

The positioning summary identifies primary/secondary proof, risks, recommended
emphasis, and a do-not-claim list. Application answers correspond to the
explicit ordered question list and retain their own traces and warnings; the
service does not invent generic prompts to reach a fixed count.

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
bullet, the full cover letter, and each supplied-question answer. Copy controls exist
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
- required application questions have exactly one non-empty answer keyed by
  `question_id`, while optional omission and zero-question output remain valid;
- target, selection, or compiled-proof changes are detected as stale;
- regeneration does not mutate approved memory;
- unsupported edited numbers and recognized tool, skill, or deployment claims
  receive blocking warnings;
- cross-memory resume edits are detected against the exact group memory;
- corrected edits clear obsolete audit findings;
- blocking warnings prevent `READY`; and
- archived packages are hidden from the default list.

## 10. Sprint 14.1 extension

Sprint 14.1 preserves the Sprint 14 ownership, exact-memory, immutable-version,
manual-edit audit, readiness, archive/restore, and stale-output contracts while
moving writing behind a typed provider boundary. Supported providers are
`local-deterministic` and `openai`; the boundary is designed so another adapter
can be added without moving business logic out of the package service.

### Provider and pipeline contract

The provider receives only minimum relevant target context, an explicit ordered
application-question list, semantically grouped requirements, 2-4 selected
compiled memories, eligible approved enrichment/proof context, labeled
strategy signals, prohibited claims, and missing proof. It returns structured
job understanding, grouped coverage, a claim plan, positioning, resume groups,
cover letter, answers keyed to supplied questions, reviewer questions, proof
suggestions, evidence references, unsupported-claim candidates, strategy notes,
and quality-review notes.

The stages are semantic job understanding, memory ranking and default
selection, claim planning, draft generation, recruiter critique, optional
rewrite, and deterministic validation. Broad concepts such as analytics,
reporting/communication, modeling, data quality, and research/problem solving
can match equivalent approved proof. Python, SQL, R, Java, cloud platforms,
Docker, Kubernetes, deployment, LLM/RAG/agent work, Tableau, Power BI, and other
concrete tools require direct approved proof.

The local provider requires no key and produces natural narrative, concise
resume-grade bullets, and direct snippets without internal "approved evidence"
language or mechanical field concatenation. A missing metric alone is not a
readiness blocker.

### OpenAI and data-policy contract

The OpenAI adapter uses the Responses API, strict Structured Outputs,
`store=false`, server-side credentials, configurable models/timeout/output
limits/reasoning effort, and at most one bounded structured repair.
Authentication,
billing, rate-limit, timeout, refusal, malformed output, and provider failures
produce safe actionable errors. The default is one `gpt-5.6-terra` call;
`gpt-5.6-sol` review is disabled unless explicitly enabled. A failed optional
review preserves valid Terra output. Every result is deterministically
validated before persistence.

`APPLICATION_WRITER_DATA_POLICY=private` permits minimized approved user data
for an appropriate non-shared project. `demo-shared` permits only seeded or
explicit demo profiles and rejects obvious identifiers server-side. The live
smoke is gated by `RUN_LIVE_OPENAI_TESTS=true`, requires `demo-shared`, and uses
the fictional Maya Chen fixture. The final post-hardening smoke remains pending
until the user explicitly approves it.

### Workspace contract

Recommended and selected memories are separate, only 2-4 are selected by
default, and saved manual removals/order are respected. Requirement coverage,
warnings, and evidence are grouped; quality review and provider/model metadata
are concise. Existing editable/copyable output, versions, `READY`, archive/
restore, and stale-output protections remain regression-critical.

### Sprint 14.1.1 claim contract and validator hardening

Sprint 14.1.1 replaces free-text evidence labels as the primary provider claim
contract with immutable server-authored evidence atoms. Each atom preserves a
stable evidence/approved-claim ID, canonical-memory ownership, optional
enrichment and proof-artifact IDs, direct source references, factual statement,
supported tools/methods, structured outcome, allowed certainty, support type,
and prohibited expansions. Target context and inferred framing remain distinct
from direct factual proof.

The output contract classifies positioning, resume bullets, cover-letter
sections, and application answers as candidate-facing. Each requires exact
structured claim metadata: field path/text, evidence-atom IDs, claim type,
tools, outcome, and certainty. Job understanding, requirement coverage,
unsupported requirements, missing-proof warnings, claims not to make, reviewer
questions, proof suggestions, target-job tool lists, strategy notes, critic/
quality notes, and validation notes are analysis-only. Unsupported tools are
allowed in those gap/warning surfaces but blocked in candidate-facing text
without direct atom support.

Structured outcomes carry evidence source, action, object, result, qualifier,
certainty, and optional metric. Semantic normalization allows harmless wording
changes while deterministic checks reject changed objects/actions/results,
metric changes, certainty inflation, unknown references, and cross-project
leakage. Concrete tools, cloud/deployment, production, monitoring, and
infrastructure claims require direct proof explicitly listed on a cited atom.

The pre-persistence sanitizer can remove only a clearly separable optional
unsupported-warning sentence. It records every removal in validation metadata
and never rewrites a central factual claim. Material failures reject the entire
new version, preserving the prior immutable package. Failure output is limited
to the stable rule/code, section, field path, normalized phrase, evidence IDs,
expected category, and surface classification; secrets, prompts, private
context, full provider output, and hidden reasoning are never included.

Regression coverage is mock-only and includes harmless outcome paraphrase,
changed object/metric/certainty, cross-project leakage, analysis-only versus
candidate-facing tool mentions, deployment claims, syntax-derived unknown
tools, factual action tails, collective-actor changes, unstructured outcomes,
safe-prefix injection, unknown/context-only atom references, recorded safe
removal, refusal to repair a material claim, redacted smoke diagnostics, and
preservation of the prior version on provider failure. The completed non-live
verification passed backend Ruff, all 343 backend tests,
Alembic current/check at `20260717_0012 (head)`, frontend lint and typecheck, all
52 frontend tests, and the production build (14/14 pages generated).

No database change is required for Sprint 14.1.1. It reuses the JSON-backed
Sprint 14.1 version fields and leaves migration `20260717_0012` unchanged.

### Sprint 14.1.2 application question/answer contract

The package owns an ordered `application_questions` input. Each question has
`question_id`, `question_text`, `required`, optional `maximum_length`, optional
`response_type`, and `relevant_target_requirement_ids` where applicable. The
question list is supplied on create/update and passed into generation. Neither
provider may infer the expected answer count or manufacture generic questions.

Every returned application answer has `question_id`, `answer`,
`evidence_reference_ids`, `evidence_atom_ids`, `tools_claimed`,
`outcome_claimed`, `certainty`, and `validation_metadata`. Deterministic
structural validation requires exactly one non-empty answer for every required
question, rejects unknown and duplicate IDs, and preserves input order. An
optional unanswered question may be omitted. Zero questions requires zero
snippets. Failures use the precise codes
`MISSING_REQUIRED_APPLICATION_ANSWER`, `DUPLICATE_APPLICATION_ANSWER`,
`UNKNOWN_APPLICATION_QUESTION_ID`, `EMPTY_APPLICATION_ANSWER`, and
`APPLICATION_ANSWER_ORDER_MISMATCH`.

Only a missing required answer is eligible for targeted answer repair. The one
repair request includes missing question IDs/text, existing valid package
sections, relevant evidence atoms, prohibited claims, and the strict answer
schema. It cannot regenerate valid resume bullets or cover-letter sections.
CareerOS merges only repaired answers and then validates the complete package
again. Failed repair creates no new version and leaves the previous immutable
version untouched.

This structural alignment does not weaken Sprint 14.1.1. Application answers,
including repaired answers, remain candidate-facing factual claims and still
require valid evidence IDs and structured tool/outcome/certainty metadata.
Unsupported tools or outcomes remain blocked. The `private` and `demo-shared`
data-policy boundary is unchanged and applies equally to generation and repair.
The Maya Chen fixture supplies exactly three required questions: `motivation`,
`complex-data-project`, and `quality-reliability`.

Sprint 14.1.2 migration `20260721_0013` persists ordered
`application_questions` on the mutable package workspace. Final non-live
verification passed backend Ruff, all 359 backend tests, Alembic current/check
at `20260721_0013 (head)`, frontend lint/typecheck, all 52 frontend tests, and
the production build (14/14 pages generated). `RUN_LIVE_OPENAI_TESTS` remains
`false`; no live provider request was run for this alignment, and live OpenAI
acceptance remains pending.

## 11. Deferred work

- PDF/DOCX and visual resume templates;
- ATS scoring or guarantees;
- open-ended company research;
- browser extraction, autofill, and automatic submission;
- broader semantic auditing beyond the implemented saved-edit claim rules;
- guided collection of missing proof;
- package-version-linked application events and outcome tracking;
- production authentication/multi-user hardening; and
- public portfolio or hosted document publishing.
