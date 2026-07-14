# Sprint 14: Resume and Cover Letter Builder

**Status:** planning specification only.
**Implementation:** not started by this document.
**Depends on:** approved Canonical Career Memory, Project Evidence Enrichment,
Career Memory Compiler, Career Diagnosis, Proof Artifact Builder, and
Application Intelligence.

## 1. Product goal

Build a reviewed application-package workspace that turns approved career memory
into truthful, target-specific resume content, cover-letter content, and a
positioning summary. It must make the provenance and limits of each material
claim inspectable before the user saves, copies, exports, or uses the package.

The product outcome is not “generate a nice letter.” The outcome is: a user can
prepare a high-quality application from their own approved career evidence
without starting from a blank document or accidentally claiming work that
belongs to another project.

## 2. Problem and product principle

A student or early-career applicant has fragmented material: resume lines,
project notes, repositories, coursework, feedback, and job descriptions.
Generic text generation asks them to restate that material repeatedly and
usually obscures which claims are true, weak, or missing.

CareerOS has already separated raw evidence, review proposals, canonical
memory, approved enrichment, compiled profiles, proof artifacts, and outcome
signals. Sprint 14 must preserve that separation.

> The builder is a consumer of reviewed intelligence, not a new source of
> career facts.

The system may tailor emphasis, order, framing, reviewer prompts, and open
questions for a job. It must not add a tool, metric, result, role, scope,
dataset, conclusion, achievement, or causal outcome absent from eligible
support.

## 3. MVP user story

As a job seeker, I can paste a job description, choose the approved projects
and experiences I want to present, and receive a reviewable application package
that includes:

- tailored resume bullets;
- a cover-letter draft;
- a concise positioning summary;
- an evidence/claim trace;
- warnings, gaps, and unanswered reviewer questions; and
- a saveable version linked to the target opportunity and the exact selected
  inputs.

I can edit the package, but edits do not silently become canonical career
memory. I can see when changing selections makes an existing draft stale.

## 4. Scope

### In scope

- Create a package from a target opportunity/job description and selected
  approved memories.
- Compile each selected memory through the existing compiled-profile boundary.
- Deterministically select safe claim ingredients and rank them for target
  relevance.
- Produce editable resume bullets, cover-letter sections, and a positioning
  summary from those ingredients.
- Show each material claim's support, selected memory, evidence references,
  enrichment references, confidence/coverage, and warnings.
- Make unsupported, weak, ambiguous, or missing material visible.
- Keep output fresh by invalidating or clearly labeling drafts when the target,
  selected memories, or material generation inputs change.
- Save an immutable package version containing input snapshots, generated
  content, edits, claim trace, and warnings.
- Provide copy-friendly output. A basic structured export is acceptable if it
  preserves the reviewed content and caveats.
- Capture later feedback as an outcome signal through the existing bounded
  feedback path.

### Explicitly out of scope

- Automatic job application submission.
- Browser extension extraction, autofill, or website automation.
- Replacing the user's full base resume without review.
- Generic free-form chat that writes unsupported materials.
- Treating outcome feedback as proof of skills or hiring causality.
- Public portfolio publishing or hosted document sharing.
- Complex visual resume templates, DOCX/PDF fidelity work, and ATS guarantees.
- New factual inference from figures, images, or tables not already represented
  as reviewed evidence.
- Multi-user collaboration and production identity/operations expansion.

## 5. Terms and trust model

| Term | Meaning in Sprint 14 |
| --- | --- |
| Target context | The role title, company (if known), job text, and user-supplied constraints used only for relevance/framing. |
| Selected memory | An exact approved canonical `memory_id` explicitly chosen by the user. |
| Compiled profile | The transient approved-only interpretation for one selected memory. |
| Claim ingredient | A structured, factual fragment selected from compiled profile fields, with provenance and support status. |
| Material claim | A sentence or bullet assertion in resume/letter/summary derived from one or more claim ingredients. |
| Claim trace | The mapping from a material claim to memory IDs, evidence IDs, enrichment IDs, and support/warning metadata. |
| Package draft | Unsaved, editable output whose freshness depends on its selected inputs. |
| Package version | An immutable saved snapshot of target, inputs, content, trace, warnings, and user edits. |
| Outcome signal | Approved feedback useful for future strategy, explicitly not factual proof. |

The factual boundary for a package is:

```text
current user
  + exact selected approved memory IDs
  + approved enrichment attached to each exact memory
  + linked, eligible evidence
  -> compiled profiles
  -> claim ingredients / outputs
```

No broad “all memories matching this title” lookup may replace exact selected
IDs. No consumer may derive factual content from a proposed/rejected/archived
enrichment, another user's records, or a target job description.

## 6. Functional requirements

### 6.1 Target and selection

1. The user can start from an existing application opportunity/draft where
   available or enter target title, company, and job description manually.
2. The workspace presents approved memories that are eligible for selection;
   it may recommend candidates but never selects a different memory ID without
   the user's visible choice.
3. The selected set, ordering, target text, output choices, and optional
   constraints form a draft input fingerprint.
4. The system compiles each selected memory separately. It does not merge
   profiles merely because titles or topics sound similar.
5. If selections change after generation, visible content is cleared into a
   new-draft state or labeled stale with an explicit regenerate action. It must
   never appear to be generated for the new selection.

### 6.2 Claim selection and tailoring

1. Claim selection consumes compiled profile fields, existing eligible proof
   artifacts, and diagnosis findings. It preserves per-ingredient provenance.
2. Target context may score relevance and choose emphasis. It cannot contribute
   factual content.
3. A claim needs at least one eligible support reference and must name only
   supported methods, tools, outputs, findings, or constraints.
4. The system should prefer specific, concrete, modest wording over inflated
   synonyms. It should preserve uncertainty and inconclusive findings.
5. If required evidence is thin, the system emits a warning/gap or reviewer
   question. It does not manufacture a quantified impact.
6. A user edit is allowed as a draft edit. If it removes or adds a material
   factual assertion, the trace must show it as user-edited and request
   confirmation/review where support is insufficient.

### 6.3 Resume output

The initial package should generate:

- a role positioning headline or summary;
- selected project/experience sections;
- tailored bullets with action, context, method, and supported result/learning
  where available;
- a skills/relevance suggestion that distinguishes supported from merely
  target-requested skills; and
- gaps/reviewer questions for material requirements not safely evidenced.

The builder should favor a small number of high-quality bullets over a long
keyword list. It should never imply that a project was deployed, productionized,
led a team, improved a business metric, or used a tool unless support exists.

### 6.4 Cover-letter output

The initial cover-letter draft should have a reviewable structure:

1. target-specific opening and legitimate motivation;
2. one or two strongest selected proof stories;
3. role-relevance connection based on approved skills/methods;
4. an honest closing and next-step request.

The letter may mention target requirements as a response context. It must
clearly distinguish “my approved experience” from “what this role requests.”
It should not invent enthusiasm, company research, network connections, or
business knowledge that the user has not provided or verified.

### 6.5 Review, provenance, and warnings

Every generated output section must expose a review path. The user should be
able to inspect:

- the exact selected memory/project;
- source evidence excerpts or stable evidence references;
- approved enrichment used;
- existing proof artifact/diagnosis references if used;
- whether support is strong, partial, weak, or absent;
- compiler/service version and generation timestamp; and
- warnings, missing evidence, role relevance, and any user edit needing review.

Warnings must be visible in the main workspace, not hidden only in developer
logs or an API response. Examples:

- “No approved metric supports a quantitative impact claim.”
- “This tool is requested by the role but is not supported by selected memory.”
- “This output is stale because selected projects changed.”
- “Outcome feedback is shown as a strategy signal, not project proof.”

### 6.6 Save and history

1. Saving creates an immutable package version. Editing a saved package creates
   a new version; it must not mutate the historical snapshot.
2. A saved version stores the original target snapshot, selected-memory IDs,
   compiled-profile/provenance snapshots or stable versions, content, traces,
   warnings, draft edits, and output status.
3. Users can reopen a past package and see the historical material plus the
   inputs used at that time, even if current enrichment later changes.
4. Later application events/feedback link to the package version and remain
   outcome signals. They do not rewrite it.

## 7. Proposed backend design

This section is an implementation proposal, not a claim about current schema or
API state. Follow existing project conventions and refine names only when
necessary.

### 7.1 Suggested persistence model

Introduce a parent package plus immutable versions:

```text
application_packages
  id, user_id, opportunity_id?, display_name, status,
  created_at, updated_at

application_package_versions
  id, application_package_id, version_number,
  target_snapshot_json,
  selected_memory_ids_json,
  input_fingerprint,
  compiled_profile_snapshots_json,
  generated_content_json,
  claim_ledger_json,
  warnings_json,
  user_edits_json,
  generator_version,
  created_at
```

Constraints should ensure ownership, ordered versions, and an immutable
historical record. If existing application-draft data already provides a
compatible parent/target relationship, reuse it deliberately rather than
creating parallel sources of truth.

The first implementation may keep structured package sections in JSON where
that fits existing persistence patterns. Normalize only fields that need
querying, filtering, tracking, or referential enforcement.

### 7.2 Claim ledger contract

Every material claim should serialize a conservative ledger entry similar to:

```json
{
  "claim_id": "resume-bullet-2",
  "surface": "resume",
  "text": "Analyzed approved spectroscopy data and documented uncertainty limits.",
  "memory_ids": ["selected-memory-id"],
  "evidence_ids": ["evidence-id"],
  "enrichment_ids": ["approved-enrichment-id"],
  "proof_artifact_ids": [],
  "diagnosis_ids": [],
  "support_level": "strong",
  "warnings": [],
  "user_edited": false,
  "strategy_signal_ids": [],
  "strategy_signal_caveat": null
}
```

An outcome signal must never appear as the sole factual support. If shown in a
package, it belongs in a strategy/review field and carries an explicit
`strategy signal, not proof of causality` caveat.

### 7.3 Services

Suggested service responsibilities:

| Service | Responsibility |
| --- | --- |
| Package input resolver | Validates current user, target context, exact selected approved memories, and input fingerprint. |
| Package compiler adapter | Calls the Career Memory Compiler independently for each selected memory and returns provenance-aware profiles. |
| Claim selection service | Selects/ranks safe claim ingredients using relevance without mutating factual fields. |
| Draft composition service | Creates structured resume, cover-letter, and positioning draft sections from claim ingredients. |
| Claim audit service | Builds ledger entries, detects unsupported/weak claims, and attaches warnings/questions. |
| Package version service | Saves immutable snapshots and retrieves historical versions. |
| Outcome-link service | Links later feedback without turning it into evidence. |

Use local deterministic composition as the baseline. If a provider-backed
rewriter is introduced later, it must receive only the already selected safe
ingredients and pass the same claim-audit gate before its text is shown.

### 7.4 API shape (proposed)

```text
POST   /api/application-packages/drafts
GET    /api/application-packages/{package_id}
GET    /api/application-packages/{package_id}/versions/{version_id}
POST   /api/application-packages/{package_id}/versions
POST   /api/application-packages/{package_id}/drafts/regenerate
POST   /api/application-packages/{package_id}/outcomes
```

A draft-create/regenerate request should include target context, ordered
`selected_memory_ids`, desired sections, and optional user constraints. The
response should include structured sections, claim ledger, warnings, reviewer
questions, input fingerprint, provenance, and freshness status.

Authorization and query filters must enforce user ownership at every package,
version, memory, enrichment, evidence, proof artifact, and outcome lookup.

## 8. Proposed frontend experience

### 8.1 Workspace layout

The initial page should prioritize review rather than a single text box:

| Area | Purpose |
| --- | --- |
| Target panel | Job title/company/job description, target requirements, and relevance context. |
| Memory selection panel | Explicit approved-memory selection, recommendations, coverage, and project identity. |
| Package draft panel | Editable positioning summary, resume sections, and cover-letter sections. |
| Claim inspector | Selected claim's evidence, enrichment, source/project, support level, and caveats. |
| Warnings/gaps panel | Missing proof, unsupported edits, target mismatches, and stale state. |
| Version/history panel | Save status, historical versions, and link to later application outcome. |

### 8.2 Freshness behavior

The following changes invalidate a generated draft: selected memory list/order,
target job text/title, desired output type, core constraints, or a material
source/profile change detected before save.

On invalidation:

- preserve user-entered target text and selection;
- do not relabel old text as new output;
- clearly show a “new draft required” or “regenerate” state;
- retain old content only as explicitly stale/reviewable context when useful;
- prevent a stale draft from being saved as though it reflects new inputs.

### 8.3 Accessibility and clarity

Warnings must be keyboard reachable, visible without hover, and paired with
plain-language remedies. Avoid color-only support levels. The UI must name the
selected project on output panels so a user can quickly detect a boundary
mistake.

## 9. Critical boundary examples

### Gas Kinematics

For a selected Gas Kinematics memory, resume/letter claims may use approved
Gas evidence and enrichment such as spectroscopy, morphology, GALFIT,
uncertainty, quality control, and honest inconclusive findings. They must not
mention UNICORN image categorization, t-SNE, or labeling work.

### UNICORN

For a selected UNICORN memory, claims may use approved image/FITS inspection,
detection review, categorization, t-SNE, data-quality, and documentation
evidence. They must not mention Gas H-alpha, [NII], CEERS/RUBIES, GALFIT,
`sigma_gas`, or morphology work.

### Sparse project

When a selected project has a title and broad context but no approved method,
output, or metric, generate modest context only and create questions/gaps. Do
not elevate target keywords into a claim.

### Outcome feedback

An approved “this framing led to an interview” item may inform a strategy
suggestion, such as revisiting a framing. It cannot support a resume bullet
claim that the user has a skill or drove an outcome.

## 10. Test plan

### Backend regression coverage

- Package input accepts only current-user, explicitly selected, approved memory
  IDs.
- Compiler adapter includes approved enrichment for the selected memory.
- Proposed, rejected, archived, foreign, and mismatched-memory enrichment is
  excluded.
- Gas and UNICORN package claim ledgers remain isolated in both directions.
- Resume and letter drafts use compiled detail rather than raw broad-memory
  title/details.
- Target keywords change relevance/ordering but cannot introduce unsupported
  facts.
- Sparse inputs produce warnings/questions rather than invented metrics or
  outcomes.
- Outcome signals are labeled strategy-only and cannot be factual support.
- Input fingerprint detects selected-memory and target changes.
- Immutable save/version behavior preserves historical input/content/ledger.
- Ownership checks cover parent, version, evidence, enrichment, proof artifact,
  diagnosis, and outcome paths.

### Frontend regression coverage

- Selected-memory names and source boundaries render in the package workspace.
- Claim inspector shows evidence/enrichment support and accessible warnings.
- Changing selection or target clears preview or visibly marks the draft stale.
- Gas preview never displays UNICORN title/details; UNICORN never displays Gas
  title/details.
- Unsupported target skill and sparse-project warnings are visible.
- User edits show changed/review-needed state where appropriate.
- Save creates/opens a new version without silently replacing prior content.
- Outcome signal copy includes the non-proof caveat.

### Local smoke paths

1. **Gas / Data Scientist Intern:** select only Gas, generate all surfaces,
   inspect Gas evidence/enrichment trace, verify uncertainty language and no
   UNICORN vocabulary.
2. **UNICORN / AI Engineer Intern:** select only UNICORN, verify its image
   inspection/categorization trace and no Gas vocabulary.
3. **Selection switch:** generate for Gas, switch to UNICORN, verify old output
   is stale/new-draft rather than mislabeled, then regenerate.
4. **Sparse proof:** choose a minimally supported memory and verify questions
   and warnings replace invented claims.
5. **Outcome signal:** attach approved feedback and verify it is strategy-only,
   not the basis of a resume/letter assertion.

## 11. Acceptance criteria

Sprint 14 is complete when:

- A user can create a target-specific resume-bullet set, cover-letter draft,
  and positioning summary from selected approved memories.
- Every material generated claim has an inspectable ledger trace or is marked
  unsupported/user-edited with a visible warning.
- Generated content uses compiled selected-memory profiles and approved
  enrichment, not unbounded raw records.
- Gas and UNICORN details never cross project boundaries.
- Target context tailors relevance without adding facts.
- Outcome signals remain explicitly non-proof.
- Selection/target changes make prior output visibly stale or start a new
  draft; stale output is never saved as current.
- Saved package versions are immutable and preserve the inputs, output,
  provenance, warnings, and edits used at that time.
- Backend lint/tests/migration checks and frontend lint/typecheck/tests/build
  pass, including the boundary regressions above.
- A new reviewer can complete the local Gas or UNICORN smoke path and explain
  why each important claim appears.

## 12. Deferred decisions

Decide during implementation only after the trust-preserving vertical slice is
working:

- whether the first export is plain copy, Markdown, HTML, PDF, or DOCX;
- whether package sections are fully normalized or initially stored as
  structured version JSON;
- how much target parsing can remain deterministic before a provider is useful;
- whether existing Application Intelligence drafts become the package parent;
- what explicit user-review control is needed for free-form factual edits; and
- which metrics best validate personal/demonstration MVP usage.

None of these decisions should delay the core evidence-trace, selected-memory,
freshness, and immutable-version guarantees.
