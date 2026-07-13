# Application Draft Quality

## Status

Implemented and merged as the Sprint 9.5 quality follow-on. This spec records
the rules that turn Application Intelligence output into usable first-person
answers.

## Problem

An application draft can be technically grounded and still fail the user if it
reads like internal planning notes. Repeating the question, saying “CareerOS
found,” listing every skill, or exposing selection metadata makes the answer
generic and unnatural. A draft must sound like the student while remaining
strictly evidence-backed.

## Goal

Produce concise, direct, role-aware draft variants that use one strong primary
memory and a small number of supporting memories. Keep provenance, gaps, and
selection reasoning in metadata and UI—not in the answer prose.

## User flow

1. The user chooses an opportunity or a specific question.
2. CareerOS determines question intent and ranks candidate approved memories.
3. Draft selection chooses one primary memory and up to two supporting memories,
   applying question-type and memory-type preferences.
4. The user chooses Short, Medium, or Detailed length.
5. CareerOS generates a first-person answer with direct role fit, relevant
   actions, and evidence-backed context.
6. The workspace displays the answer with selected memories, evidence counts,
   matched themes, and gaps nearby.
7. The user edits, copies, saves, or marks the draft approved. Editing changes
   the draft state; it does not change canonical memory.

## Core concepts

- **Draft variant**: the same grounded selection expressed at a different
  length. `SHORT`, `MEDIUM`, and `DETAILED` are the supported variants; `LONG`
  remains a compatibility alias.
- **Primary memory**: the single strongest approved project, experience, or
  other memory for the prompt.
- **Supporting memory**: a limited secondary memory used to add skills,
  education, collaboration, or context.
- **Question intent**: the inferred purpose of a prompt, such as why this role,
  leadership, technical skills, or project explanation.
- **Quality metadata**: structured provenance and selection data that lets the
  user inspect a draft without polluting the answer.

## Data model / backend behavior

`application_drafts` stores the opportunity/question scope, draft type, prompt,
draft text, evidence IDs, status, metadata, and timestamps. The current
metadata contract includes:

- requested length and user-facing variant label;
- `uses_approved_memory_only`;
- matched memory IDs;
- primary memory metadata: ID, title, type, evidence count, and themes;
- supporting memory metadata with the same fields;
- question type when applicable;
- deduplicated evidence IDs;
- bounded gaps for the opportunity.

Draft generation uses the ranked application matches but applies a second
selection pass. Project and experience memories receive priority for project or
experience prompts; skill sets support technical prompts; education and
programs provide context when appropriate. The implementation prefers one
primary memory and no more than two supporting memories.

The generator applies quality rules for direct first-person phrasing, role
relevance, natural tool names, and length. It avoids “I would highlight,”
“CareerOS found,” question repetition, unsupported claims, and exhaustive skill
lists. SQL is preferred over MySQL when a role asks for SQL generally. LaTeX is
excluded unless the opportunity involves writing, documentation, research,
academic work, or technical publishing. Skill support is filtered to the role.

The draft is saved as `DRAFT`. A text update moves it to `EDITED`; an explicit
status update can mark it `APPROVED` or `ARCHIVED`. These are artifact states,
not application submission events.

## Frontend behavior

The draft studio should show:

- variant controls that make length differences obvious;
- answer text as the primary surface;
- selected primary and supporting memories as inspectable context;
- evidence count and theme labels;
- gaps and the approved-memory-only signal;
- copy, edit, save, approve, and status feedback;
- clear distinction between “saved draft” and “submitted application.”

Metadata should be presented as trust-building context, not debug JSON. The
answer itself should remain readable if the user copies it into a form.

## Product rules

- Ground every factual statement in approved memory and retained evidence IDs.
- Keep one clear story spine; do not concatenate unrelated memories.
- Answer the prompt before adding context.
- Prefer concrete actions and role-relevant tools over a skills dump.
- Keep selection metadata outside prose.
- Do not use a gap as a reason to invent a qualification.
- Treat every generated draft as editable and user-owned.
- Approval of a draft does not submit it or mutate the source memory.

## Known limitations

- The current generator is deterministic and template-based.
- It cannot reliably match an individual student’s voice or all cultural
  expectations of a specific employer.
- It has no outcome signal yet to learn which variant or wording performs best.
- “Quality” is currently groundedness, relevance, and readability—not a
  validated hiring-success metric.
- Long-form cover letters and resume layout remain broader artifact problems.

## Future follow-ups

- Add user voice preferences and lightweight style memory.
- Add direct user ratings for relevance, specificity, and genericness.
- Compare draft variants against eventual application and interview outcomes.
- Add claim-level validation and contradiction checks.
- Support structured artifact revisions and immutable submission snapshots.
