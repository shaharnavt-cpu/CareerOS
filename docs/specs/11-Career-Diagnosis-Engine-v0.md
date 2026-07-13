# Career Diagnosis Engine v0

## Status

Proposed next direction after the merged Sprint 10 MVP. This is a product and
technical specification for the Sprint 11 foundation; it is not an implemented
backend or frontend feature.

## Problem

Overlooked students rarely need another generic resume rewrite. They need help
understanding why their evidence is not being recognized, which claim is
under-supported, and what concrete action would improve their trajectory next.

CareerOS already has approved memory, application matching, and draft
provenance. It needs a diagnosis layer that connects those signals into a
specific, evidence-weighted intervention.

## Goal

Given an approved Career Memory and a target, produce a compact diagnosis that
answers:

- what career identity is strongest right now;
- what the student can prove;
- what the target is likely to recognize;
- what proof is missing or poorly framed;
- which one action is highest leverage in the next seven days.

Sprint 11 v0 creates the foundation for this loop. It does not attempt full
outcome analytics, autonomous coaching, or a universal career recommender.

## User flow

1. The user selects a target role or program and confirms which approved Career
   Memory should be considered.
2. CareerOS optionally accepts an honest frustration/context paragraph, project
   or artifact descriptions, and notes about successful or failed applications.
3. The engine reads approved memory, available application history, and the
   supplied context.
4. The user receives a diagnosis with identity, evidence map, recognition gap,
   missing proof, confidence indicators, and one seven-day proof sprint.
5. The diagnosis offers exact next messages or actions the user can copy,
   personalize, and carry out.
6. The user can teach CareerOS a feedback note about what happened or how a
   piece of evidence should be framed. v0 stores the note as a learning input;
   it does not yet calculate statistically reliable outcome trends.

## Core concepts

- **Career identity**: the strongest current through-line across approved
  experience, skills, projects, education, and goals.
- **Evidence map**: a compact chain from identity claim to proof, validator,
  target opportunity, and known outcome.
- **Recognition gap**: the difference between what the user wants, what the
  user can currently prove, and what an evaluator is likely to recognize from
  the current presentation.
- **Missing proof**: a specific absent or weak artifact, result, validator,
  framing, or target alignment signal.
- **Proof sprint**: one feasible, high-leverage action that can produce or
  strengthen proof within seven days.
- **Do-not-waste-time warning**: a bounded warning against low-leverage work
  when the diagnosis points to a more important bottleneck.
- **Evidence strength**: how directly and reliably a conclusion is supported;
  it is separate from model confidence.
- **Teach CareerOS note**: a user-provided observation about framing, feedback,
  or an outcome that may inform future diagnosis.

## Inputs

The v0 request contract accepts:

- approved canonical Career Memory;
- application history, if available;
- target role or program;
- optional frustration or context paragraph;
- optional project or artifact descriptions;
- optional notes about successful or failed applications.

Unapproved review proposals may be shown as future work, but they must not be
treated as proof in the diagnosis.

## Outputs

The v0 response should contain:

1. **Strongest current career identity** — one plain-language sentence plus
   supporting memory IDs.
2. **Evidence map** — claims, supporting evidence, validators or missing
   validators, relevant target themes, and known outcomes.
3. **Recognition gap** — what the user wants, what they can prove, what the
   evaluator is likely to recognize, and the main bottleneck between them.
4. **Missing proof** — the smallest set of concrete proof gaps, prioritized by
   leverage and feasibility.
5. **Seven-day proof sprint** — one action with a definition of done, expected
   proof artifact, and suggested seven-day sequence.
6. **Do-not-waste-time warning** — one specific low-leverage action to defer,
   only when the evidence supports the warning.
7. **Exact next messages/actions** — draft outreach, follow-up, request for
   feedback, project framing, or application action with placeholders clearly
   marked for user editing.
8. **Confidence and evidence strength** — per major conclusion, with reasons
   and the evidence IDs or input notes used.

## Data model / backend behavior

The first implementation should be a provider-neutral diagnosis service with a
typed request and response boundary. It should read canonical memory and
existing application objects without mutating them.

The minimal v0 persistence addition is a lightweight user-owned feedback note
concept with:

- note ID and user ID;
- user-authored text;
- created timestamp and optional source context;
- optional links to an application, draft, project, or target;
- optional user labels such as success, rejection, framing, or genericness.

Examples include:

- “This cover letter got me an interview invite.”
- “Use Gas Kinematics as a data analysis story, not an astronomy story, for
  analytics roles.”
- “This draft felt too generic.”
- “This application was rejected.”
- “This project seems strongest for AI/risk roles.”

The service may return a diagnosis without persisting a full diagnosis run in
v0. If runs are persisted, store input references, output version, evidence
references, and timestamps—not hidden chain-of-thought. Historical application
and submission records must remain immutable. A user feedback note is a new
learning input; it must not rewrite the text that was submitted previously.

The initial engine may combine deterministic rules, structured retrieval, and a
replaceable reasoning provider. Every conclusion must carry its evidence
references and a reason code such as strong direct proof, corroborated proof,
framing inference, or missing evidence.

## Frontend behavior

The first workspace should be a diagnosis brief, not a chat feed. It should:

- show the selected target and input scope;
- make the identity sentence and main bottleneck prominent;
- render the evidence map as inspectable claims and proof;
- distinguish missing proof from missing ability;
- show confidence and evidence strength beside conclusions;
- present exactly one recommended proof sprint before optional ideas;
- provide copy/edit affordances for exact messages and actions;
- offer a simple “Teach CareerOS” capture action after the user reports what
  happened.

Empty states should say what input is missing, such as an approved memory or a
target role. Low-confidence diagnoses should invite the user to add context
instead of pretending certainty.

## Product rules

- Diagnose a bottleneck before recommending more work.
- Recommend one high-leverage next action, not a list of generic habits.
- Never turn a weak proof signal into a judgment about the student’s worth or
  ability.
- Never invent outcomes, validators, skills, or employer preferences.
- Keep user-provided feedback distinct from system inference.
- Explain the evidence behind every strong conclusion.
- Preserve user agency: messages and actions are drafts for review, not
  autonomous outreach.
- Treat seven days as a planning horizon, not a promise of an outcome.
- Do not optimize for cleverness outside the narrow problem of career diagnosis
  for overlooked students.

## Known limitations

- v0 will have sparse application and outcome history for most users.
- Recognition likelihood is an inference from target text and available
  evidence, not a ground-truth employer model.
- User feedback notes are not yet statistically aggregated.
- The engine cannot establish causality from one successful or failed
  application.
- Diagnosis quality depends heavily on the completeness and approval quality of
  Career Memory.

## Future follow-ups

- Add outcome-linked diagnosis runs and longitudinal learning.
- Build the full Evidence Graph and validators described in the North Star.
- Compare diagnosis recommendations with application, outreach, project, and
  recommendation outcomes.
- Add target-specific recognition models with transparent evaluation.
- Let the engine revise a proof sprint when new feedback arrives.
- Add privacy controls, export, and deletion for feedback notes.
