# CareerOS Domain Model

Version: 0.1

Status: Draft

Last Updated: July 2026

---

# Purpose

The Domain Model defines the software representation of CareerOS.

While the Knowledge Model explains *what* CareerOS knows conceptually, the Domain Model specifies *how* that knowledge is represented within the application.

This document serves as the authoritative contract between product design and implementation.

All database schemas, backend models, API contracts, and frontend forms should be derived from this document.

---

# Design Principles

## Product Before Code

The software implementation should always reflect the product design—not the other way around.

The Domain Model ensures that implementation decisions remain consistent with CareerOS's long-term vision.

---

## Single Source of Truth

Every real-world fact should exist exactly once.

Generated artifacts (resumes, cover letters, interview answers, networking messages, etc.) should reference canonical knowledge rather than duplicate it.

---

## Explicit Relationships

Relationships between entities should be intentional and documented.

Examples include:

- Person → Education
- Person → Experience
- Experience → Skills
- Project → Evidence
- Application → Resume Snapshot

Relationships should never be left to implementation assumptions.

---

## Human Readable

This document is written for both engineers and product designers.

Every entity should be understandable without reading code.

---

# Entity Specification

Every domain entity should define the following:

## Purpose

Why the entity exists.

## Fields

Each field should include:

- Name
- Data type
- Required or optional
- Default value (if applicable)

## Relationships

Each relationship should specify:

- One-to-one
- One-to-many
- Many-to-many

along with the related entity.

## Constraints

Examples include:

- Required uniqueness
- Validation rules
- Maximum lengths
- Immutable fields

## Ownership

Every entity should specify ownership.

Future versions should support multi-user architecture using `user_id`.

---

# Entity Lifecycle

Every entity should define its lifecycle.

Questions include:

- Can it be edited?
- Can it be deleted?
- Should it be soft deleted?
- Should previous versions be retained?
- Should timestamps be recorded?

Standard timestamps should include:

- Created At
- Updated At

Some entities may additionally require:

- Deleted At
- Archived At

---

# Versioning

CareerOS distinguishes between editable knowledge and historical snapshots.

Canonical knowledge is editable.

Generated outputs and submitted application materials should remain immutable after creation.

Versioning should preserve historical accuracy without preventing future improvements.

---

# Validation

Each entity should define validation requirements.

Examples include:

- Required fields
- Accepted value ranges
- Enumerated values
- Referential integrity
- Duplicate prevention

Validation should occur before persistence whenever possible.

---

# Evidence

Evidence is a first-class entity within CareerOS.

Every important professional claim should be supported by evidence whenever available.

Examples include:

- Research papers
- GitHub repositories
- Certificates
- Publications
- Performance metrics
- Awards
- Screenshots
- Portfolio links

Generated content should reference evidence rather than unsupported claims.

---

# Relationships

The domain model is relational but conceptually forms a connected knowledge graph.

Examples include:

Person

↓

Experience

↓

Project

↓

Skill

↓

Application

↓

Interview

↓

Outcome

The application should store these relationships explicitly to support explainable recommendations and long-term learning.

---

# Future Expansion

The Domain Model should evolve without requiring large architectural changes.

Future entities may include:

- Certifications
- Organizations
- Events
- Publications
- Patents
- Courses
- Networking Conversations
- Recruiting Campaigns
- AI Recommendations

New entities should integrate into the existing model without modifying established principles.

---

# Guiding Principle

The Domain Model exists to ensure that CareerOS remains consistent across product design, database architecture, backend implementation, frontend development, and AI systems.

Every implementation should begin with the Domain Model rather than inventing structure during development.
