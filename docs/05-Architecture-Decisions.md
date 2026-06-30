# CareerOS Architecture Decisions

Version: 1.0

Status: Accepted

---

# Purpose

This document records architecture decisions that have been intentionally made for CareerOS.

These decisions should guide future implementation unless they are explicitly revised.

---

# AD-001: Repository Structure

Status: Accepted

Decision:

CareerOS will use a single monorepo.

Reasoning:

The project is currently maintained by a small team.

A monorepo simplifies:

- shared code
- documentation
- AI development
- versioning
- deployment

Future versions may split repositories if scale requires it.

---

# AD-002: Architecture Style

Status: Accepted

Decision:

CareerOS will begin as a modular monolith.

Reasoning:

Separate modules are easier to maintain than one large codebase while avoiding the operational complexity of microservices.

Modules should communicate through well-defined interfaces even when running inside the same application.

---

# AD-003: Career Knowledge is the Source of Truth

Status: Accepted

Decision:

Canonical career knowledge is editable.

Generated documents are not.

Applications reference snapshots of canonical knowledge at submission time.

Reasoning:

The user should always be able to improve their profile without rewriting history.

---

# AD-004: Submission Snapshots are Immutable

Status: Accepted

Decision:

Each submitted application stores an immutable snapshot of:

- resume
- cover letter
- generated answers
- job description
- supporting evidence

Reasoning:

CareerOS must always know exactly what was submitted.

Historical applications should never silently change after submission.

---

# AD-005: Applications are Mutable

Status: Accepted

Decision:

Applications evolve over time.

They may gain:

- recruiter responses
- interview stages
- assessments
- offers
- rejection reasons
- reflections
- lessons learned

The application record remains the central timeline for the hiring process.

---

# AD-006: Evidence is First-Class

Status: Accepted

Decision:

Every AI-generated claim should reference supporting evidence.

Examples:

- Project
- Experience
- Achievement
- Coursework
- Certification

Unsupported claims should never be automatically included.

Reasoning:

This supports the guiding principle that CareerOS never hallucinates experience.

---

# AD-007: Human Approval

Status: Accepted

Decision:

CareerOS may recommend actions but never performs important actions without user approval.

Examples include:

- resume generation
- cover letter generation
- application submission
- strategy changes

---

# AD-008: AI is an Advisor

Status: Accepted

Decision:

AI assists with reasoning and generation.

Deterministic logic should always be preferred when possible.

Examples:

Deterministic:

- dates
- GPA
- filenames
- calculations
- timelines

AI:

- tailoring
- summarization
- writing
- recommendations

---

# AD-009: Provider Independence

Status: Accepted

Decision:

CareerOS should never depend on a single AI provider.

Every AI interaction must go through a provider-independent interface.

Supported providers may change over time.

---

# AD-010: MVP Scope

Status: Accepted

The first production version focuses on one complete workflow:

1. Maintain structured career knowledge.
2. Analyze a job description.
3. Generate a tailored resume.
4. Generate a tailored cover letter.
5. Review and edit.
6. Save the application.
7. Track the outcome.

Browser automation, autofill, and advanced integrations are future milestones.

---

# AD-011: Engineering Philosophy

CareerOS is not a document generator.

CareerOS is a professional operating system.

Documents are outputs.

Career knowledge is the product.
