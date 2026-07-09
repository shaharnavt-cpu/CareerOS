# Knowledge Review Intelligence

Knowledge Review Intelligence is the boundary between Universal Listening and
user-approved Career Memory. It keeps three concepts deliberately separate:

- **Evidence** is an immutable observation extracted from a source. Page labels,
  transcript rows, dates, and repeated text remain stored for provenance.
- **Review proposals** are editable, evidence-backed interpretations such as one
  education record, experience, project, achievement, or skill set.
- **Career Memory** contains only proposals the user explicitly approves.

## Evidence grouping

The listening repository persists and deduplicates evidence before synthesis.
`KnowledgeReviewIntelligence` then reads fused evidence clusters, filters
low-value display noise, and combines related facts into structured proposals.
For example, institution, degree, field, track, and graduation evidence from a
resume and transcript become one education proposal with citations to both
sources. Repeated skills become one skill-set proposal.

Evidence that does not warrant its own card is not deleted. The API reports it
as `hidden_supporting_evidence_count`, allowing the UI to say that supporting
evidence was saved quietly while keeping the review queue manageable.

## Review and clarification lifecycle

Every proposal has a user-facing proposal type, review status, confidence,
structured fields, source names, supporting evidence count, and reasoning
summary. Proposals remain editable and default to `NEEDS_REVIEW`; high
confidence is a display priority, not automatic approval.

An open clarification belongs to a specific proposal. The onboarding client
keeps that proposal ID while asking the question. The next user answer updates
the pending proposal, clears the clarification, records its resolution time,
and acknowledges the resolved fields. It does not rerun the original evidence
through reasoning, so the same question is not immediately repeated.

The local deterministic provider uses the same synthesis layer and requires no
external API key. This makes proposal counts and structured smoke-test results
repeatable during development.
