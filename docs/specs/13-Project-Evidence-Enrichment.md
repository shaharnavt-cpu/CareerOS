# Project Evidence Enrichment + Memory Identity Resolution v0

## Status

Implemented in Sprint 13. CareerOS can resolve new project evidence against
approved canonical memory, create reviewed enrichment instead of duplicate
project drafts, project approved enrichment into canonical JSON, and reuse the
result in Proof Artifact Builder and Career Diagnosis.

The implementation remains local deterministic and requires no LLM key.

## Problem

Detailed project documents often repeat a shorter project description already
approved from a resume. Treating every description as a new memory fragments
provenance, burdens review, and leaves downstream artifacts dependent on whichever
thin duplicate happens to be selected.

## Goal

Given a project title and source-backed detail, CareerOS should choose a safe
review path:

- create a new memory;
- enrich an existing approved memory;
- avoid an exact duplicate proposal;
- flag a possible merge;
- retain quiet supporting evidence;
- ask the user when identity is ambiguous.

No path may auto-merge distinct canonical memories or bypass explicit enrichment
approval.

## User flow

1. Open `/enrichments` from Career Memory, Review, Proof, or navigation.
2. Select an approved project memory.
3. Paste project-specific context, method, findings, limitations, or outputs.
4. Generate a proposed structured enrichment.
5. Inspect identity reasoning, confidence, fields, sources/evidence, and warnings.
6. Edit, approve, or reject the proposal.
7. Regenerate a proof artifact or rerun diagnosis after approval.

An existing possible-duplicate review card can instead be converted to enrichment.

## Trust boundary

- Listening evidence and pasted text are observations.
- Enrichment records are reviewed interpretations of those observations.
- Only `APPROVED` enrichment is projected into canonical Career Memory.
- Rejected and archived enrichment cannot guide proof artifacts or diagnosis.
- Original canonical fields and provenance are preserved.
- The resolver stores concise reasons, not hidden chain-of-thought.
- No finding, method, dataset, metric, tool, or outcome may be added without
  supporting text.

## Identity resolution contract

Resolution values:

- `CREATE_NEW`
- `ENRICH_EXISTING`
- `DUPLICATE_PROPOSAL`
- `POSSIBLE_MERGE`
- `QUIET_SUPPORTING_EVIDENCE`
- `NEEDS_USER_CONFIRMATION`

The response contains:

- confidence in `[0, 1]`;
- matched memory ID/title when present;
- matched proposal ID when present;
- deterministic reason summaries;
- evidence IDs;
- recommended review action.

High-confidence project matches create a proposed enrichment during durable
proposal persistence and skip the duplicate project proposal. Medium-confidence
matches remain reviewable with `_identity_resolution` metadata. Exact pending
proposal titles reuse the existing proposal.

Stable named-project disagreement is a negative signal. In particular, UNICORN
must not merge into Gas Kinematics merely because both concern astronomy or share
an institution.

## Persistence

`career_memory_enrichments` is the durable review history. Its status values are
`PROPOSED`, `APPROVED`, `REJECTED`, and `ARCHIVED`. Its enrichment types are:

- `PROJECT_CONTEXT`
- `PROJECT_METHOD`
- `PROJECT_RESULT`
- `PROJECT_LIMITATION`
- `PROJECT_OUTPUT`
- `PROJECT_ROLE_RELEVANCE`
- `PROJECT_FULL_ENRICHMENT`
- `MEMORY_MERGE_SUGGESTION`

The table stores target memory, optional source, source label, structured JSON,
evidence IDs, confidence, reasoning, identity resolution, warnings, and
timestamps.

Approval rebuilds the target memory's complete enrichment projection from all
currently approved enrichment records. This makes approval, rejection, and
archival reversible without overwriting original fields.

## Extraction contract

Supported structured keys:

- `project_title`
- `project_goal`
- `research_question`
- `data_or_inputs`
- `tools_or_methods`
- `analysis_steps`
- `findings_or_results`
- `limitations`
- `outputs`
- `collaborators_or_context`
- `role_relevance`
- `role_specific_framing`
- `skills_demonstrated`
- `resume_bullet_claims`
- `cover_letter_angles`
- `proof_artifact_angles`
- `proof_artifact_summary`
- `warnings_not_to_claim`

The extractor supports labeled lines and bounded sentence matching. It may derive
future-use framing only from supported problem/method text. It cannot infer an
absent result or quantified impact.

Low-detail input returns a parse-quality warning and retains the available detail
instead of failing or pretending full understanding.

## Downstream integration

Proof Artifact Builder gives approved enriched fields priority for the project
problem, inputs, method, findings, limitations, context, relevance, and warnings.
Supported Gaussian fitting and inconclusive/no-clear-trend findings remain visible.
Channel variants derive from those same sections.

Career Diagnosis consumes the same approved JSON projection. An enriched project
can strengthen evidence themes and add a Recognition Gap note explaining that
method, data, and limitations are documented. Diagnosis does not read proposed,
rejected, or archived enrichment directly.

## Future resume and cover-letter builders

No full resume or cover-letter generation is included. Approved enrichment
exposes reusable claims and angles plus warnings. Future builders must retain the
same evidence checks, provenance, and approval boundary.

## API contract

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/memory-identity/candidates` | Rank approved identity candidates for supplied title/text. |
| `GET` | `/api/career-memory/enrichments` | List user-owned enrichment records. |
| `POST` | `/api/career-memory/{memory_id}/enrichments` | Create a proposed enrichment from pasted text or saved evidence. |
| `GET` | `/api/career-memory/{memory_id}/enrichments` | List enrichment history for one memory. |
| `POST` | `/api/career-memory/{memory_id}/enrichments/from-proposal/{proposal_id}` | Convert a duplicate project proposal into enrichment. |
| `PATCH` | `/api/career-memory/enrichments/{id}` | Edit or change enrichment status. |

## Acceptance criteria

- Similar Gas Kinematics titles resolve to the approved capstone memory.
- UNICORN remains a distinct project.
- A high-confidence upload match does not persist a duplicate project proposal.
- Enrichment targets only approved user-owned canonical memory.
- Evidence IDs and source labels persist.
- Approval updates the canonical enrichment projection without destroying the
  original payload.
- Rejection and archival remove enrichment from downstream use.
- Proof Artifact Builder uses approved fields and ignores rejected fields.
- Diagnosis recognizes stronger documented project proof.
- Low-text inputs explain how to add better project evidence.
- Local deterministic mode needs no provider key.

## Limitations and follow-ups

- Add an interactive recent-source/evidence picker to the frontend.
- Add richer aliases and user-managed alternate titles.
- Add canonical memory revisions and explicit multi-memory merge review.
- Add OCR and bounded extraction for figures, tables, posters, and slides.
- Add semantic retrieval only after deterministic provenance and evaluation are
  mature.
