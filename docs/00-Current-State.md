# CareerOS: Current State

## Read this first

CareerOS is a career-intelligence system for turning messy student experience
into reviewed, reusable, role-specific professional proof. It is not a generic
resume generator, a cover-letter chatbot, or a job tracker with text generation
attached.

Its differentiator is a clean professional-memory layer: CareerOS keeps source
evidence, user review, approved memory, project enrichment, and derived career
materials separate and inspectable.

This document is the current handoff snapshot. For the system's trust model,
read [26-Intelligence-Architecture.md](26-Intelligence-Architecture.md). For
the next implementation sprint, read
[14-Resume-Cover-Letter-Builder.md](specs/14-Resume-Cover-Letter-Builder.md).

## What exists today

CareerOS currently supports this core loop:

```text
Universal Listening
  -> Reviewable Career Memory
  -> Approved Canonical Memory
  -> Project Evidence Enrichment
  -> Career Memory Compiler
  -> Diagnosis / Proof Artifact / Application Intelligence
  -> Teach CareerOS outcome signals
```

The implemented product surfaces include:

| Module | Current capability |
| --- | --- |
| Universal Listening | Accepts supported source material and extracts evidence plus reviewable proposals using deterministic local mode. |
| Career Memory review | Lets the user approve, edit-approve, reject, or otherwise resolve proposals into durable canonical memory. |
| Canonical Career Memory | Stores user-owned, approved career facts and their evidence/source references. |
| Project Evidence Enrichment | Attaches deeper project methods, findings, limitations, and outputs to an existing approved project without creating a duplicate memory. |
| Memory identity resolution | Uses deterministic, conservative matching to identify likely enrichment, duplicate, or possible-merge paths. |
| Career Memory Compiler | Compiles one selected approved memory plus its approved enrichment into a transient, provenance-aware profile. |
| Career Diagnosis | Assesses proof, gaps, and next actions from approved memory; approved outcome feedback remains a labeled strategy signal. |
| Proof Artifact Builder | Produces editable, versioned, evidence-backed case studies and channel variants from one selected memory. |
| Application Intelligence | Parses opportunities, matches approved memory, exposes gaps, and creates editable application-response drafts. |
| Teach CareerOS | Captures feedback/outcome signals for future strategy without rewriting factual proof. |

## Current architecture

CareerOS is a modular monolith:

- Frontend: Next.js, React, TypeScript, and Tailwind CSS in `frontend/`.
- Backend: FastAPI, SQLAlchemy, Alembic, and Python in `backend/`.
- Database: PostgreSQL 16, normally started locally with Docker Compose.
- Reasoning: deterministic local mode is supported without an LLM key. A
  provider-compatible path exists for later use but is not required for local
  development or the current proof workflow.

The important data flow is:

```text
Source document / pasted note / conversation
  -> listening evidence
  -> review proposal
  -> approved canonical memory
  -> approved enrichment for that exact memory
  -> compiled memory profile
  -> diagnosis, proof artifact, application intelligence
```

The compiler is transient: it is created from approved records at read time and
does not become another canonical source of truth. Saved artifacts and drafts
retain their own historical snapshot/provenance.

## Trust boundaries that must remain intact

CareerOS is valuable only if its generated materials remain trustworthy.

- The current user and exact selected `memory_id` define the factual boundary.
- Only approved canonical memory and approved enrichment for that same memory
  can support factual claims.
- Proposed, rejected, archived, foreign, or unlinked enrichment cannot affect a
  compiled profile.
- Evidence from another memory cannot be borrowed because a title sounds
  similar.
- Approved outcome feedback can guide strategy or framing, but is not evidence
  that the user has a skill or that a document caused an outcome.
- Target role and job text affect relevance and framing, never the underlying
  facts, tools, metrics, methods, or results.
- Missing evidence must remain visible as a gap or warning instead of being
  filled with plausible language.

The two current astronomy-project examples make this concrete:

- **Gas Kinematics** can use approved spectroscopy, morphology, uncertainty,
  and analysis evidence, but cannot use UNICORN image-labeling details.
- **UNICORN** can use approved image inspection, categorization, and t-SNE
  evidence, but cannot use Gas Kinematics H-alpha, GALFIT, CEERS/RUBIES, or
  `sigma_gas` details.

## Strongest current demo path

The most convincing current demonstration is not a generic document prompt. It
shows the memory-to-proof loop:

1. Open a project in **Enrich** and attach source-backed detail to the existing
   approved project memory.
2. Approve the enrichment and see its memory-quality impact, project boundary,
   and missing evidence prompts.
3. Show that pasting the same evidence again creates no duplicate and produces a
   visible, actionable warning.
4. Open **Proof**, choose the same project and a target role, and generate a
   case study from the compiled profile.
5. Change the selected memory and show that the prior artifact disappears into a
   new-draft state instead of being mislabeled as the new project.
6. Optionally use **Diagnosis** or **Applications** to show the same approved
   project evidence informing gaps and opportunity matching.

For a concise proof demo, use:

- Gas Kinematics + `Data Scientist Intern` to demonstrate data, validation,
  uncertainty, and an inconclusive result handled honestly.
- UNICORN + `AI Engineer Intern` to demonstrate image-data quality, labeling,
  exploratory organization, and human-in-the-loop review without claiming a
  deployed ML system.

## Local development snapshot

The expected local services are:

| Service | Default address | Notes |
| --- | --- | --- |
| Next.js frontend | `http://localhost:3000` | Run from `frontend/` or with the root frontend script. |
| FastAPI backend | `http://localhost:8000` | Health: `/api/health`; interactive docs: `/docs`. |
| PostgreSQL | `localhost:5432` | Docker Compose service name: `database`. |

The committed `.env.example` configures local PostgreSQL and
`REASONING_PROVIDER=local-deterministic`. Use the exact Windows CMD setup and
test commands in [27-Claude-Code-Handoff.md](27-Claude-Code-Handoff.md).

## What is not built yet

The product has intelligence and proof foundations, but it does **not** yet
include:

- a reviewed Resume and Cover Letter Builder;
- saveable application-package snapshots containing those materials;
- guided career interviewing that fills memory gaps conversationally;
- source-aware figure, table, slide, or OCR understanding;
- a seeded, one-click showcase/demo mode;
- a complete application package tracker and submission timeline;
- browser-extension extraction or autofill;
- production authentication, multi-user operations, hosted exports, or public
  portfolio publishing.

Those omissions are deliberate. The next document-generation feature must
reuse the approved-memory and compiled-profile boundary rather than bypass it.

## Known limitations

- Deterministic project recognition is bounded vocabulary/pattern matching, not
  open-ended semantic interpretation.
- Current document intelligence is strongest for extractable text. It does not
  claim to understand charts, figures, tables, or images that were not extracted
  into evidence.
- The compiler has explicit Gas Kinematics and UNICORN patterns, while other
  projects receive generic, conservative compilation.
- Current generated proof is editable and versioned, but its visual templates,
  document exports, and public presentation are intentionally limited.
- Outcome data is sparse and is never treated as proof of causality.
- The current local experience is development-oriented; deployment, security,
  and operational hardening need their own scoped work before broad use.

## What to build next

Sprint 14 should build a **Resume and Cover Letter Builder** on top of the
existing intelligence layer. It should package approved, compiled career proof
for a target opportunity while keeping an evidence trace and unsupported-claim
warnings visible. It must not become an unconstrained text generator.

See [25-Roadmap-to-MVP.md](25-Roadmap-to-MVP.md) for the recommended sequence
and [14-Resume-Cover-Letter-Builder.md](specs/14-Resume-Cover-Letter-Builder.md)
for the implementation-ready product/technical spec.
