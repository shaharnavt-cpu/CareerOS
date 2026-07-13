# Knowledge Review Intelligence

## Status

Implemented and merged as the Sprint 7 architecture. This document is a
formal backfill of the behavior that now sits between Universal Listening and
approved Career Memory.

## Problem

Universal Listening can recover many useful facts from resumes, transcripts,
projects, and other career sources, but raw extraction is not yet usable
memory. A document contains repeated lines, labels, dates, course rows, and
partial descriptions. Creating one card per extracted line produces noise,
duplicates, and unsupported interpretations.

CareerOS needs a review boundary where evidence can be grouped into concise,
editable proposals without silently turning an inference into a fact.

## Goal

Turn persisted evidence clusters into a small, explainable review queue. Each
proposal should say what CareerOS thinks it found, why it thinks that, which
source evidence supports it, and what the user must decide. Approved proposals
become Career Memory; pending or rejected proposals do not.

## User flow

1. The user uploads or pastes a career source through Universal Listening.
2. Listening normalizes, deduplicates, and groups source observations into
   evidence clusters.
3. Knowledge Review Intelligence combines related observations into proposals
   such as education, experience, project, program, achievement, or skill set.
4. The review workspace shows proposal type, title, structured fields,
   confidence, reasoning, source names, evidence excerpts, and supporting
   evidence count.
5. The user edits a proposal when wording or fields are incomplete, answers an
   open clarification when one is needed, and explicitly approves or rejects.
6. Only approval is allowed to project the proposal into canonical Career
   Memory. Other surfaces consume that approved projection.

## Core concepts

- **Evidence** is an observation from a source. It retains provenance and is
  not the same thing as a conclusion.
- **Evidence cluster** is a fused group of related observations from one or
  more sources.
- **Review proposal** is an editable, evidence-backed interpretation of a
  cluster. It is not canonical until the user approves it.
- **Supporting evidence** is useful evidence that does not require its own
  visible card. It remains counted and retrievable.
- **Clarification** is a question attached to one proposal when a missing or
  conflicting field prevents a reliable interpretation.
- **Confidence** is a reasoning signal and display priority. It never means
  automatic approval.

## Data model / backend behavior

The synthesis boundary accepts `EvidenceCluster` records from Universal
Listening and returns a `ReviewSynthesisResult` containing proposals,
`evidence_considered`, and `hidden_supporting_evidence_count`.

Each `KnowledgeProposal` contains, at minimum:

- stable proposal ID, entity type, and proposal type;
- structured `proposed_value` fields;
- operation and review/approval state;
- confidence from 0 to 1;
- one or more `EvidenceReference` records with source ID, source type, title,
  excerpt, location, evidence ID when persisted, and corroboration metadata;
- a reasoning summary;
- optional clarification and proposal relationships;
- source names and supporting evidence count.

The current synthesis pass deliberately groups related evidence for education,
achievements, programs, experiences, projects, skill sets, contacts, and
fallback clusters. It deduplicates proposals and caps the review queue so
supporting detail does not overwhelm the user. Low-value transcript and
document noise is filtered from the visible queue but is not treated as
deleted evidence.

The provider boundary remains interchangeable. The local deterministic
provider uses the same synthesis and validation contract so development and
smoke tests do not require an external model key. The knowledge API exposes
proposal creation, proposal review, proposal editing, review-proposal listing,
dashboard summary, and canonical memory reads.

## Frontend behavior

The review workspace is a workbench, not a chat transcript. It should:

- group proposals by meaningful memory type;
- make approval state, review status, evidence, source names, confidence, and
  reasoning visible;
- allow focused editing before a decision;
- show a clarification inline with the proposal that owns it;
- keep the user on the review surface after save, approve, reject, or an error;
- explain that hidden supporting evidence was saved when the visible card count
  is lower than the evidence count.

The UI should preserve the distinction between “CareerOS inferred this” and
“the user approved this.”

## Product rules

- Never create a canonical fact without an explicit user approval.
- Every visible proposal must have at least one evidence reference.
- Preserve source identity, excerpt, and location whenever available.
- High confidence changes ordering or emphasis; it does not bypass review.
- A clarification belongs to one proposal and must not be asked globally.
- Editing a proposal returns it to a reviewable state.
- Rejected or pending proposals must not be used as application evidence.
- Deduplication may reduce cards, but it must not erase supporting evidence.
- Generated summaries must remain explainable without exposing hidden chain of
  thought.

## Known limitations

- The current local provider is deterministic and rule-based rather than a
  broad semantic understanding system.
- Evidence clustering is bounded by the source formats and vocabulary known to
  the current implementation.
- Clarifications are persisted with the proposal, but there is not yet a rich
  conversational resolution history.
- Multi-user identity and production authorization are not the focus of this
  Sprint 7 backfill.
- Proposal-to-typed-domain-entity projection is still a partial bridge around
  the durable canonical memory projection.

## Future follow-ups

- Add stronger cross-source conflict resolution and provenance inspection.
- Improve extraction for arbitrary project descriptions, portfolios, and
  recommendation letters.
- Add proposal version history and an audit trail for user decisions.
- Support user-defined evidence and correction feedback as learning signals.
- Use the approved memory and evidence graph as inputs to Career Diagnosis
  Engine v0, defined in `11-Career-Diagnosis-Engine-v0.md`.
