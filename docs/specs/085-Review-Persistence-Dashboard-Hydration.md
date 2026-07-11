# Review Persistence and Dashboard Hydration

## Status

Implemented and merged as the durable review/persistence follow-on to Sprint
7. This document formalizes how review state survives requests and how
dashboard surfaces hydrate from it.

## Problem

An in-memory review queue is useful for a prototype but breaks the product
contract. A refresh can lose a proposal, approval can fail to appear on the
dashboard, and downstream story or application surfaces cannot tell the
difference between a generated suggestion and an approved fact.

CareerOS needs a durable lifecycle with one clear write boundary: the user
decision is persisted, and approval creates or updates the canonical Career
Memory projection.

## Goal

Persist proposals, edits, decisions, and approved memory in PostgreSQL. Make
review and dashboard reads restart-safe, idempotent for the same proposal
identity, and explicit about what is pending, reviewed, canonical, or merely
supporting evidence.

## User flow

1. Reasoning produces proposals from listening evidence.
2. The review service upserts them into durable review state. Existing pending
   or clarification records may be refreshed; resolved decisions are not
   silently overwritten.
3. The user opens or refreshes `/review`; the client loads persisted proposals
   instead of relying on the previous browser render.
4. The user edits, approves, or rejects a proposal. An edit returns it to a
   reviewable state; approval or rejection records the decision time.
5. Approval creates or updates one canonical memory record keyed by the user's
   stable proposal identity. Its structured fields, evidence IDs, source IDs,
   confidence, and originating proposal remain linked.
6. The dashboard reads the persisted projection and shows counts, completeness,
   recent approved memories, pending review, and suggested next actions.

## Core concepts

- **Durable review proposal**: the persisted, user-facing interpretation and
  its current decision state.
- **Canonical memory projection**: the approved, downstream-readable record.
- **Identity key**: a normalized hash of the proposal type and identifying
  fields, used to avoid duplicate canonical memories for one user.
- **Review decision**: explicit approval or rejection, with edited approval
  distinguished from an untouched approval.
- **Dashboard hydration**: loading current counts and recent canonical memory
  from the backend rather than reconstructing them from local UI state.

## Data model / backend behavior

The persistence boundary currently uses two primary tables.

### `review_proposals`

Stores the durable proposal ID, user ID, proposal/entity type, title, identity
key, serialized proposal data, decision, edited flag, optional canonical entity
ID, and review timestamp. Decision values include pending review, needs
clarification, approved, edited approved, and rejected.

### `canonical_memory_records`

Stores the approved projection: user ID, identity key, memory type, title,
structured fields, evidence IDs, source IDs, confidence, originating review
proposal ID, optional typed entity ID, and timestamps. `(user_id,
identity_key)` is unique. This record is the current approved Career Memory
surface used by dashboard, story, and application features.

The review repository performs these invariants:

- upserts only refresh proposals that are still pending or awaiting
  clarification;
- an edit stores the new proposal data, marks it edited, and returns it to
  pending review or clarification;
- an approved edited proposal is stored as `EDITED_APPROVED`;
- approval upserts the canonical memory projection and refreshes its evidence,
  source, structured fields, confidence, and timestamps;
- rejection records the decision but does not create canonical memory;
- all reads and writes are scoped to the current user.

The dashboard summary returns type counts, canonical total, pending review
count, reviewed count, total proposal count, supporting evidence count, a
bounded profile completeness score, and recent canonical memories. Supporting
evidence is counted from persisted listening evidence, not inferred from the
number of visible cards.

## Frontend behavior

The review page hydrates its proposal list and summary on load. The dashboard
hydrates from the dashboard endpoint and should remain useful in three states:

- loading: communicate that approved Career Memory is being loaded;
- empty: explain that approving proposals will hydrate the dashboard;
- failure: show a clear error and a retry action without implying that data was
  deleted.

After a decision, the review UI refreshes the durable state and the dashboard
reflects the same canonical count on the next read. Local browser summaries may
support transition polish, but they are not a source of truth.

## Product rules

- “Approved Career Memory” means persisted canonical memory, not a generated
  proposal.
- Dashboard counts must be explainable from durable records.
- Refreshing a page must not duplicate a proposal or canonical memory.
- Re-reviewing a rejected proposal requires an explicit new user action; it is
  not silently re-approved by reprocessing the source.
- Approval must preserve the evidence trail that justified the proposal.
- A dashboard error must never be presented as zero career memory.
- Persistence failure must be visible and retryable.

## Known limitations

- The current demo path uses a stable demo user identity and is not a complete
  production authentication/tenant boundary.
- Canonical memory is a projection with flexible JSON fields; typed entity
  synchronization is not yet universal.
- Profile completeness is a lightweight heuristic based on populated memory
  categories, not a career-quality score.
- There is no full event-sourced history of every edit or decision yet.

## Future follow-ups

- Add proposal revisions, decision audit events, and conflict history.
- Replace the demo identity with authenticated tenant-scoped access.
- Add explicit canonical-memory versioning and safe merge tooling.
- Hydrate story and application workspaces from the same shared memory query
  layer.
- Record user feedback and outcomes as append-only learning data without
  changing historical submissions.
