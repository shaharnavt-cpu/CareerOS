# Sprint 05 — Multi-Source Listening Engine

> Status: Planning Specification  
> Version: Draft 1.0  
> Mode: Implementation Guide

---

## Objective

Implement the first version of the CareerOS Multi-Source Listening Engine.

Sprint 4 taught CareerOS how to reason over proposed knowledge. Sprint 5 teaches CareerOS how to listen to multiple sources of evidence before reasoning.

The goal is not merely to parse files. The goal is to convert user-provided sources into standardized evidence objects, fuse related evidence, and feed that evidence into the Knowledge Reasoning Engine.

---

## Product Goal

By the end of Sprint 5, a user should be able to provide one or more sources, such as a resume, transcript-like text, LinkedIn-style profile text, conversation input, or manual entry, and see CareerOS produce evidence-backed knowledge proposals.

The user experience should feel like:

```text
Upload or paste sources
        ↓
CareerOS listens
        ↓
Evidence is extracted
        ↓
Related evidence is grouped
        ↓
Knowledge proposals are generated
        ↓
The user reviews and approves
```

CareerOS should not treat any single source as absolute truth. Each source is one partial telling of the user's story.

---

## Core Principle

CareerOS listens before it reasons.

A source listener should not directly create canonical knowledge. It should produce evidence.

Reasoning should happen only after evidence has been normalized, attributed, and fused.

---

## Architecture

Sprint 5 introduces the listening layer before the existing reasoning pipeline.

```text
Raw Source
        ↓
Source Adapter
        ↓
Listener
        ↓
Evidence Objects
        ↓
Evidence Fusion
        ↓
Knowledge Reasoning Engine
        ↓
Knowledge Proposals
        ↓
User Review
        ↓
Career Memory
```

---

## Required Backend Capabilities

### 1. Source Types

Support a source type model that can represent:

- resume
- transcript
- LinkedIn export/profile
- conversation
- manual entry
- generic document

PDF and DOCX support should be implemented if practical within the existing dependency constraints. If binary parsing is not practical in this sprint, support plain text extraction fixtures and design the interfaces so binary parsing can be added later without redesign.

---

### 2. Source Adapter Interface

Create a reusable interface for converting raw source input into normalized source records.

Each normalized source should include:

- source id
- source type
- original filename or label
- raw text
- metadata
- received timestamp
- user id or tenant context where applicable

---

### 3. Listener Services

Implement listener services that convert normalized source content into evidence objects.

At minimum, implement listeners for:

- resume-like text
- transcript-like text
- LinkedIn/profile-like text
- conversation/manual text

Listeners should identify evidence fragments such as:

- education mentions
- program mentions
- experience mentions
- project mentions
- skill mentions
- achievement mentions
- date mentions
- organization mentions
- role/title mentions
- links or external references

Listeners should not over-reason. Their job is evidence extraction, not final classification.

---

### 4. Evidence Object Model

Every evidence object should include:

- evidence id
- source id
- source type
- raw text excerpt
- normalized text where useful
- evidence category
- location metadata
- extraction confidence
- timestamps
- optional page/section/paragraph metadata
- optional source URL or file reference

Evidence categories may include:

- education
- program
- experience
- project
- skill
- achievement
- organization
- date
- role
- contact
- link
- unknown

---

### 5. Evidence Fusion Service

Implement a service that groups related evidence objects before they reach the reasoning engine.

The fusion service should:

- group duplicate or near-duplicate evidence
- group corroborating evidence across sources
- preserve conflicting evidence instead of hiding it
- maintain provenance for every evidence item
- produce evidence clusters

Example:

```text
Evidence Cluster: GEVIP

Evidence:
- Resume: "Galaxy Evolution Vertically Integrated Program"
- Conversation: "GEVIP was my astronomy research program"
- Project section: "UNICORN Project, GEVIP"
```

---

### 6. Conflict Handling

If two sources disagree, the system should preserve both claims.

Examples:

- different dates
- different titles
- different institution names
- different project names
- incomplete or ambiguous descriptions

Conflicts should later become clarification opportunities.

---

### 7. Integration with Sprint 4 Reasoning

Evidence clusters should feed the existing Knowledge Reasoning Engine.

Do not bypass the Sprint 4 proposal and approval boundary.

The output should remain:

```text
Evidence Cluster
        ↓
Reasoning Engine
        ↓
Knowledge Proposal
        ↓
User Review
```

---

## Required Frontend Capabilities

### 1. Upload / Input Experience

Enhance the Sprint 3 upload area so users can provide sources.

At minimum, support:

- paste text source
- mock upload source state
- source type selection
- source label

If real PDF/DOCX upload is implemented, the UI should support it, but the UX should remain graceful if parsing is limited.

---

### 2. Listening Status

Replace generic loading states with listening-oriented states.

Examples:

```text
Listening to your resume...
Finding education evidence...
Finding project evidence...
Comparing sources...
Preparing knowledge proposals...
```

The UX should reinforce that CareerOS is understanding evidence, not simply processing a file.

---

### 3. Evidence Review Visibility

Where possible, show users why CareerOS believes something.

The review UI should display:

- source name
- excerpt
- confidence
- evidence category
- whether evidence was corroborated by another source

---

## API Requirements

Add or extend API endpoints for:

- submitting sources
- listing extracted evidence
- generating proposals from evidence
- reviewing/approving proposals

Exact endpoint design may follow existing backend conventions.

Suggested endpoints:

```text
POST /api/listening/sources
GET /api/listening/sources
GET /api/listening/evidence
POST /api/listening/proposals
```

Do not break existing Sprint 4 endpoints.

---

## Data Persistence

Persist enough information to support source provenance.

At minimum:

- sources
- evidence objects
- evidence clusters if appropriate
- proposal links to evidence

If full persistence is too large for this sprint, implement the database models and tests for the core concepts while keeping some execution paths in memory. Clearly report any temporary in-memory behavior.

---

## Out of Scope

Do not implement:

- full production OCR
- full LinkedIn API integration
- GitHub API integration
- browser extension ingestion
- email/calendar ingestion
- resume generation
- job matching
- application tracking
- social/shared Career Memory
- Career Memory Explorer visualization

---

## Testing Requirements

Add tests for:

- source normalization
- listener output
- evidence object creation
- evidence fusion
- conflict preservation
- proposal generation from fused evidence
- API behavior
- frontend build

Existing backend and frontend tests must continue passing.

---

## Acceptance Criteria

Sprint 5 is complete when:

1. CareerOS accepts at least one user-provided source.
2. Source content becomes standardized evidence objects.
3. Related evidence can be fused into clusters.
4. Evidence clusters can feed the reasoning engine.
5. Proposals preserve source provenance.
6. Users can see evidence supporting a proposal.
7. The approval boundary remains intact.
8. Existing Sprint 3 and Sprint 4 workflows still work.
9. Tests and builds pass.

---

## Definition of Done

Sprint 5 is complete when CareerOS can listen to multiple forms of user-provided career evidence, preserve provenance, fuse related evidence, and pass that evidence into the reasoning engine to produce explainable, user-approved knowledge proposals.

CareerOS should feel less like a parser and more like an assistant that listens carefully before forming conclusions.
