# Sprint 04 --- Knowledge Reasoning Engine

> Status: Planning Specification\
> Version: Draft 1.0

------------------------------------------------------------------------

# Objective

Replace the deterministic mock knowledge extraction introduced in Sprint
3 with the first implementation of the CareerOS Knowledge Reasoning
Engine.

The goal is not to build the final AI system, but to establish the
complete reasoning pipeline that transforms evidence into user-approved
Career Memory.

------------------------------------------------------------------------

# Product Goal

By the end of Sprint 4 a user should be able to:

1.  Upload a resume (or use mock input).
2.  Have CareerOS extract candidate entities.
3.  See proposed knowledge with confidence scores.
4.  Receive intelligent clarification questions only when needed.
5.  Approve, edit, or reject proposals.
6.  Update the Career Memory after approval.

------------------------------------------------------------------------

# Architecture Impact

This sprint implements the reasoning layer between:

Source Adapters

↓

Knowledge Extraction

↓

Career Memory

No feature should bypass this layer.

------------------------------------------------------------------------

# Core Design Principles

-   AI proposes; users approve.
-   Every proposal must have evidence.
-   Every clarification question must have a reason.
-   CareerOS asks only when confidence or evidence is insufficient.
-   Relationships are first-class knowledge.
-   Confidence guides review, never replaces it.

------------------------------------------------------------------------

# Backend Work

Implement modules for:

-   Source normalization
-   Entity extraction
-   Knowledge proposal generation
-   Evidence attribution
-   Confidence scoring
-   Relationship linking
-   Clarification generation
-   Approval workflow integration

Organize code into reusable services.

------------------------------------------------------------------------

# Frontend Work

Replace deterministic mock onboarding logic with API-driven proposal
objects.

Enhance the review experience to display:

-   Confidence
-   Evidence
-   Reason for clarification
-   Proposal status

Maintain the existing Sprint 3 user experience.

------------------------------------------------------------------------

# Clarification Rules

CareerOS should never ask generic questions.

Every question must reference a specific ambiguity.

Good example:

"I found GEVIP in your resume, but I couldn't determine whether it was
primarily a research program, coursework, or another structured program.
Which best describes it?"

Poor example:

"Tell me more about your education."

------------------------------------------------------------------------

# Knowledge Proposal Model

Every proposal should include:

-   Entity type
-   Proposed value
-   Confidence score
-   Supporting evidence
-   Reasoning summary
-   Required clarification (optional)
-   User decision state

------------------------------------------------------------------------

# Out of Scope

Do NOT implement:

-   Final production prompts
-   Multi-document ingestion
-   Browser extension
-   Resume generation
-   Job matching
-   Authentication
-   Production vector search

------------------------------------------------------------------------

# Acceptance Criteria

-   Proposal pipeline functioning end-to-end.
-   Evidence attached to every proposal.
-   Confidence displayed in UI.
-   Clarification questions generated only when justified.
-   User approval updates Career Memory.
-   Existing Sprint 3 UI remains functional.

------------------------------------------------------------------------

# Testing Requirements

-   Existing tests pass.
-   New reasoning services have unit tests.
-   Proposal generation is deterministic for supplied fixtures.
-   No regressions in onboarding flow.

------------------------------------------------------------------------

# Definition of Done

Sprint 4 is complete when CareerOS can transform raw career evidence
into structured, explainable, user-approved knowledge proposals while
preserving the approval boundary established in earlier sprints.
