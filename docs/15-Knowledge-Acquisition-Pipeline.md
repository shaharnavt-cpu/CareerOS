# CareerOS Knowledge Acquisition Pipeline

> Version: Draft 1.1

## Purpose

The Knowledge Acquisition Pipeline is the controlled pathway by which source-derived information becomes canonical career knowledge in CareerOS.

Documents, conversations, manual entry, and external integrations produce **knowledge proposals**. A proposal may create a canonical entity, update an existing entity, or add a relationship. It never changes canonical knowledge without explicit user approval.

This pipeline governs the editable professional profile described in the Career Knowledge Model. It does not replace the separate lifecycles for application workflow events, immutable submission snapshots, generated artifacts, or learning data.

## Architecture Invariants

- Canonical career knowledge remains the single source of truth.
- AI may propose changes but never silently commits them.
- Every proposal has source provenance; important claims should also have supporting evidence whenever available.
- Confidence prioritizes review and clarification. It is not permission to commit.
- Conflicting sources never silently overwrite canonical knowledge.
- Canonical entities remain distinct and are connected by explicit relationships rather than duplicated across contexts.
- Submitted application snapshots remain immutable when canonical knowledge changes later.
- Direct user entry and edits still pass through validation. The user's explicit save or confirmation is the approval action.

## Scope

### Supported Sources

- Resume or curriculum vitae (CV)
- Transcript
- LinkedIn export
- Guided Career Interview or other user conversation
- Manual entry
- Portfolio
- GitHub
- Browser extension
- Certificates
- Future integrations

Each source contributes provenance and may contribute evidence. A source is not automatically proof: for example, a resume can explain where a claim came from without independently verifying it.

### Canonical Targets

Proposals must map to entity types and relationships already defined by the Domain Model. Current examples include Education, Program, Experience, Project, Achievement, Skill, Contact, and their links.

Concepts such as certifications, publications, awards, leadership, activities, and organizations must map to an approved canonical entity or evidence type. A source adapter must not invent a new persistent entity type. A new type requires the normal domain-model, schema, and architecture-decision process.

## Proposal Contract

A knowledge proposal should contain enough information to review and apply the change safely:

- Target entity type and proposed operation: create, update, or link
- Proposed values and relationships
- Source reference and location, such as page, section, message, or external record
- Supporting evidence references, when available
- Confidence and a short, user-facing explanation
- Possible match to existing canonical entities
- Validation issues, missing fields, or conflicts
- Ownership and lifecycle metadata

The conceptual proposal states align with the onboarding flow:

```text
DISCOVERED -> NEEDS_REVIEW -> APPROVED -> CANONICAL
                         \-> REJECTED
```

`APPROVED` records the user's decision. `CANONICAL` means the approved change was successfully applied. Rejected or superseded proposals must never be used as canonical knowledge.

## Pipeline Overview

```text
User Source
    |
    v
Source Adapter and Normalization
    |
    v
Knowledge Extraction
    |
    v
Provenance and Evidence Attribution
    |
    v
Entity Resolution and Knowledge Linking
    |
    v
Confidence, Validation, and Conflict Detection
    |
    v
User Review and Approval
    |
    v
Canonical Commit and Audit
```

## Stage 1 — Source Adapter and Normalization

Each source adapter converts input into a common internal representation so downstream processing does not depend on the original format.

Examples:

- Resume -> parsed document with page and section locations
- Transcript -> academic records with row or page locations
- Conversation -> timestamped or message-addressable transcript
- GitHub -> repository metadata obtained with the user's authorization

Adapters should preserve source identity, ownership, timestamps, stable locations, and a content hash when practical. Reprocessing the same source should be idempotent and should not create duplicate proposals or evidence.

Imported content is untrusted input. Adapters must not execute embedded content, and AI processing must treat instructions found inside a document or external page as data rather than system instructions.

## Stage 2 — Knowledge Extraction

CareerOS extracts candidate entities, field values, and relationships using deterministic parsing where practical and provider-independent AI services where reasoning is required.

Extraction creates proposals only. It does not write to canonical entity tables. Structured outputs must be validated against the allowed domain types and field constraints before advancing.

## Stage 3 — Provenance and Evidence Attribution

Every proposal references the source material that produced it so the user can answer:

> Why does CareerOS think this?

Provenance identifies the origin of a proposal. Evidence supports or verifies a professional claim. The same item may serve both roles, but the concepts are not interchangeable.

Evidence should use the existing `evidence_items` and `evidence_links` model when it becomes canonical. Evidence and source metadata may be retained in a non-canonical staging area before approval when needed for review, retry, security, or audit.

## Stage 4 — Entity Resolution and Knowledge Linking

CareerOS compares proposals with canonical entities and other proposals in the same batch. It identifies likely duplicates, proposes matches, and suggests relationships without copying the underlying facts.

Automatic matching may reduce review work, but ambiguous merges require user confirmation. Links must preserve tenant ownership and may connect only entities belonging to the same user.

## Stage 5 — Confidence, Validation, and Conflict Detection

Confidence may consider:

- Source quality and verification status
- Agreement between independent sources
- Completeness and ambiguity
- Extraction certainty
- Match quality against existing entities

Confidence guides review order and follow-up questions; it never replaces approval or evidence. Low-confidence or high-impact proposals should be reviewed first.

When sources or canonical values disagree, CareerOS presents the competing values and their provenance. The user may keep the existing value, accept the proposed value, edit it, merge genuinely duplicate entities, or keep distinct facts when both are valid.

## Stage 6 — User Review and Approval

The review experience groups proposals by domain and clearly distinguishes proposed values from existing canonical values. Users may:

- Approve
- Edit and approve
- Reject
- Mark as unsure or request clarification
- Confirm a link or merge when supported

Approval must cover the exact values and relationships that will be committed. If an edit materially changes a proposal, validation and conflict detection run again before commit.

## Stage 7 — Canonical Commit and Audit

An approved change is applied atomically: canonical entities, relationships, and evidence links either succeed together or remain unapplied. A failed commit stays approved but not canonical until it is retried or revised.

Canonical knowledge remains editable and normally uses soft deletion. Applying a proposal must not mutate historical submission snapshots or artifact revisions.

The system should retain enough decision metadata to explain who approved the change, what proposal was applied, when it was applied, and which sources supported it. Retention must follow privacy and deletion policy; auditability does not justify retaining unnecessary raw content indefinitely.

## Operational Requirements

### Security and Privacy

- Every source, proposal, evidence item, and resulting entity is scoped to its owning user.
- Authorization is enforced at ingestion, review, and commit boundaries.
- Source adapters request the minimum external permissions required.
- Sensitive raw content is minimized in logs and AI requests.
- Hidden chain-of-thought is never stored; user-facing explanations and necessary provenance are sufficient.
- Source deletion and account deletion must propagate according to the documented retention policy.

### Reliability

- Processing is resumable after partial failure.
- Retries are idempotent.
- Adapter and extraction versions are recorded so results can be reproduced or reprocessed.
- Validation failures and unsupported entity types remain visible for review rather than being silently discarded.
- Provider outages do not bypass validation or approval.

## Relationship to Existing Architecture

This pipeline refines, rather than replaces, the existing contracts:

- `02-Career-Knowledge-Model.md` defines canonical knowledge and its relationships.
- `05-Architecture-Decisions.md` establishes editable canonical knowledge, first-class evidence, human approval, deterministic logic, and provider independence.
- `06-Domain-Model.md` defines allowed entities and lifecycles.
- `07-Database-Schema.md` defines canonical, evidence, historical snapshot, and tenant-isolation persistence rules.
- `09-AI-Architecture.md` governs provider-independent AI processing and validation.
- `12-Security-and-Privacy.md` governs PII, authorization, audit, retention, and deletion.
- `14-Onboarding-and-User-Experience.md` defines the proposal states and user review experience.

The current schema does not yet define durable source or proposal tables. Any implementation that persists those records requires an approved domain/schema update and migration; this document does not authorize an implicit schema change.

## Future Expansion

New integrations should add a source adapter and reuse the shared extraction, proposal, resolution, review, and commit stages. An integration must not bypass the pipeline simply because its data appears structured or authoritative.

## Guiding Principle

CareerOS does not learn from documents alone.

CareerOS learns from people. Documents, conversations, and external sources are evidence that help CareerOS understand a person's professional journey, while the person remains the final authority over their canonical Career Memory.
