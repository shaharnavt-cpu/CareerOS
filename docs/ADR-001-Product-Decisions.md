# ADR-001: Conversational Onboarding Product Decisions

> Status: Accepted
>
> Date: July 2026

## Context

CareerOS needs a first-use experience that helps users build structured career knowledge without requiring them to understand the underlying domain model or complete a long sequence of forms.

These decisions define the approved product direction for onboarding and govern the Sprint 3 user experience.

## Decisions

### 1. Conversation-First Onboarding

CareerOS begins with natural conversation rather than form-first data entry. Forms remain available as editing tools after CareerOS has organized the user's story into proposed structured knowledge.

### 2. Guided Story Conversation

The primary onboarding interaction is a Guided Story conversation. CareerOS starts with broad prompts, listens for connected facts, and asks focused follow-up questions when information is incomplete or ambiguous.

### 3. Upload and Conversation First Screen

The first screen presents document upload and conversation together. Users may upload existing material, begin talking immediately, or continue without documents. Upload must never block the conversational path.

### 4. Continuous Onboarding

Onboarding is not a one-time wizard. Users may return to conversation, add documents, clarify details, and expand their career knowledge throughout the life of their profile.

### 5. Programs Are First-Class Entities

Programs are canonical CareerOS entities for structured experiences that span categories such as education, research, leadership, projects, achievements, skills, and evidence. Programs must not be flattened into a single Experience or duplicated across multiple entities.

### 6. User Approval Before Canonical Storage

Extracted or inferred knowledge remains proposed until the user approves it. CareerOS may recommend structure and ask for clarification, but it must not silently promote proposed knowledge into canonical storage.

### 7. Live Knowledge Panel

The Guided Story experience includes a Live Knowledge Panel that updates as the conversation progresses. It groups proposed knowledge by domain, displays confirmation or review status, and makes uncertainty visible without interrupting the conversation.

## Consequences

- Sprint 3 may use realistic mock data and interactions to establish the complete experience without persistence, parsing, authentication, or LLM integration.
- The interface must clearly distinguish confirmed knowledge from items that need review.
- Program must appear alongside Education, Experience, Projects, Skills, and Achievements wherever onboarding knowledge is summarized.
- Later backend and AI work must preserve user approval as the boundary between proposed and canonical knowledge.
