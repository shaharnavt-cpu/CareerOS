# Application Intelligence

## Status

Implemented and merged as Sprint 9. Application Intelligence is the first
downstream consumer that turns an opportunity into an evidence-backed fit map
and an editable response draft.

## Problem

Students often have relevant experience but do not know which part of their
Career Memory to use for a particular opportunity. Generic application tools
either ask the user to start from a blank page or generate unsupported claims.
CareerOS needs to connect a job or application question to approved memory,
show what matches, and make gaps visible before drafting.

## Goal

Analyze a pasted opportunity, classify its requirements and questions, rank
relevant approved Career Memory, expose evidence-backed gaps, and create an
editable first draft. The feature is an intelligence layer; it does not submit
applications or control a browser.

## User flow

1. The user pastes a job description, internship posting, or application text.
2. CareerOS detects a title, organization when present, role type, skills,
   keywords, responsibilities, and questions.
3. The user may add a specific application question. CareerOS classifies its
   likely type and intent, such as project explanation, leadership, technical
   skills, or experience example.
4. CareerOS matches the opportunity or question to approved canonical memory.
   Each match shows score, reason, matched themes, and evidence IDs.
5. The workspace shows gaps where the opportunity asks for proof not present in
   approved memory.
6. The user requests a general or question-specific draft, chooses a length,
   edits it, and may mark it approved for their own workflow.

## Core concepts

- **Opportunity**: the raw pasted text plus a structured analysis.
- **Question**: a prompt attached to an opportunity with type, intent, and
  required themes.
- **Approved-memory match**: a ranked relation between one opportunity scope
  and one canonical memory record.
- **Evidence-backed gap**: a requirement for which the current approved memory
  does not supply adequate proof; it is not a claim that the user lacks the
  underlying ability.
- **Draft**: an editable response generated from selected approved memories.
- **Story context**: approved story material that may provide additional
  narrative context without replacing canonical memory evidence.

## Data model / backend behavior

Application Intelligence persists four related concepts.

- `application_opportunities` stores user ID, title, organization, raw text,
  detected role type, detected skills, keywords, responsibilities, questions,
  status, and timestamps.
- `application_questions` stores opportunity ID, question text, question type,
  detected intent, required themes, status, and timestamps.
- `application_memory_matches` stores opportunity/question scope, canonical
  memory ID, match score, human-readable match reason, matched themes, and
  evidence IDs. The scope/memory combination is unique.
- `application_drafts` stores opportunity/question scope, draft type, prompt,
  text, evidence IDs, status, and JSON metadata.

The API supports opportunity creation/list/read, match recomputation, question
creation, opportunity/question drafting, and draft updates. The current local
analysis is deterministic: keyword and role vocabulary detects requirements,
then normalized terms, memory type, evidence availability, and question-type
boosts rank candidates. Match reasons are persisted so the UI does not need to
reconstruct why a result appeared.

The service reads `canonical_memory_records` only. Pending, rejected, or
unapproved review proposals are excluded. If no approved memory covers a
detected requirement, the service adds a bounded gap rather than fabricating a
match. Approved story records may be returned as context, but drafts retain
canonical evidence IDs as their traceability base.

## Frontend behavior

The application workspace should make the relationship legible:

- opportunity analysis is shown before drafting;
- detected skills, themes, and responsibilities are visible;
- matches show memory title, match reason, evidence count, and themes;
- gaps are framed as proof opportunities, not deficit judgments;
- general and question-specific drafting are separate actions;
- the user can inspect selected memories and evidence metadata around a draft;
- copy and save/edit controls are available without treating a draft as a
  submission.

The dashboard links to Applications only when approved memory exists, while the
workspace remains able to explain that more review is needed when memory is
empty.

## Product rules

- Match and draft only from approved canonical memory.
- Never infer employment, project results, tools, or outcomes that are not in
  approved memory.
- Preserve the raw opportunity text as the source for analysis.
- Every match must include a reason and evidence IDs when available.
- A gap is useful only when tied to a detected requirement or theme.
- Application Intelligence may recommend a memory; the user remains the author
  and approver of the final response.
- Browser filling, submission, and automated recruiter communication are out of
  scope for this layer.

## Known limitations

- The current analyzer is deterministic and vocabulary-driven.
- It does not reliably understand every job family, synonym, or ambiguous
  question.
- It does not track actual application submissions, interview events, or
  outcomes yet.
- Opportunity records are not a full recruiting CRM and do not replace the
  historical application model described in the broader database spec.
- Drafts are starting points; they are not guaranteed to be optimal or ready
  to submit without user review.

## Future follow-ups

- Add richer opportunity parsing and semantic retrieval after the evidence graph
  is in place.
- Add application lifecycle, submission snapshots, and outcome events.
- Connect recognition-gap analysis to application matching and target roles.
- Add user feedback on whether a match or draft was useful.
- Let a future browser surface consume approved drafts without changing the
  intelligence boundary.
