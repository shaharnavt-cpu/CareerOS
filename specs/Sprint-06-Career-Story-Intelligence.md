# Sprint 06 — Career Story Intelligence

Status: Planning Specification

## Objective
Teach CareerOS to transform Career Memory into coherent Career Stories.

## Product Goal
- Discover potential stories from Career Memory.
- Suggest story groupings.
- Explain why experiences belong together.
- Ask clarification questions.
- Let users approve, edit, merge, split, or reject stories.
- Store approved stories as first-class objects.

## Story Hierarchy
Career
-> Stories
-> Chapters
-> Experiences
-> Entities
-> Evidence

Stories may overlap in time and experiences may belong to multiple stories.

## Story Discovery
Use shared goals, organizations, collaborators, projects, skills, chronology, conversations, and evidence confidence.
AI proposes; users approve.

## Story Model
- title
- summary
- primary goal
- transformation
- chapters
- experiences
- entities
- evidence
- confidence
- status

## Backend
Implement:
- story discovery
- story clustering
- story summarization
- story persistence
- story approval

Reuse the Listening and Reasoning engines.

## Frontend
Create a Story Workspace for reviewing, editing, approving, merging and splitting stories.

## Out of Scope
Resume generation, interview preparation, Career Explorer rendering, browser extension.

## Definition of Done
CareerOS understands coherent professional stories that can power downstream features such as resumes, interviews, networking, and visualization.
