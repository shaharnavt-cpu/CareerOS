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
Sprint 14's implemented package workflow, read
[28-Application-Package-Builder.md](28-Application-Package-Builder.md).

## What exists today

CareerOS currently supports this core loop:

```text
Universal Listening
  -> Reviewable Career Memory
  -> Approved Canonical Memory
  -> Project Evidence Enrichment
  -> Career Memory Compiler
  -> Diagnosis / Proof Artifact / Application Intelligence / Application Package
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
| Application Package Builder | Produces positioning, tailored bullets, a cover letter, snippets, proof suggestions, grouped evidence/warnings, quality review, and immutable versions through local or optional GPT-5.6 writing; deterministic validation remains the save gate. |
| Teach CareerOS | Captures feedback/outcome signals for future strategy without rewriting factual proof. |

## Current architecture

CareerOS is a modular monolith:

- Frontend: Next.js, React, TypeScript, and Tailwind CSS in `frontend/`.
- Backend: FastAPI, SQLAlchemy, Alembic, and Python in `backend/`.
- Database: PostgreSQL 16, normally started locally with Docker Compose.
- Reasoning: deterministic local mode is supported without an LLM key. The
  application-writing provider boundary supports improved local generation and
  an optional OpenAI Responses API path. No key is required for local
  development or automated verification.

The important data flow is:

```text
Source document / pasted note / conversation
  -> listening evidence
  -> review proposal
  -> approved canonical memory
  -> approved enrichment for that exact memory
  -> compiled memory profile
  -> diagnosis, proof artifact, application intelligence, application package
```

The compiler is transient: it is created from approved records at read time and
does not become another canonical source of truth. Saved artifacts and
application-package versions retain their own historical input, profile,
provenance, warning, and output snapshots.

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

For Build Week or any shared demo-project traffic, use only the fictional Maya
Chen fixture described in
[30-Build-Week-Demo-Data-and-Privacy.md](30-Build-Week-Demo-Data-and-Privacy.md).
The historical Gas/UNICORN examples below remain useful local regression paths,
not approved personal-data inputs for the shared project.

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
6. Open **Application Packages**, enter the target, select the same approved
   memory, and generate a positioning summary, resume bullets, cover letter,
   snippets, traces, and unsupported-claim warnings.
7. Change the target or selected proof and show the stale state, then regenerate
   to append a new immutable version.

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

## Sprint 14.1 application-writing intelligence

Sprint 14.1 places a provider-neutral seam between ranked compiled evidence and
version persistence. `local-deterministic` remains the default; `openai` uses a
strict structured Responses API request with `store=false`. The cost-safe live
default is `gpt-5.6-terra`, with `gpt-5.6-sol` review disabled unless explicitly
enabled. Every provider result passes deterministic evidence, claim, quality,
and data-policy checks before an immutable version can be saved.

The pipeline groups job requirements semantically, recommends and selects 2-4
strong memories by default, plans claims, drafts, critiques, and can optionally
rewrite. The workspace groups requirement coverage, warnings, and evidence by
memory, and shows concise quality and provider metadata while preserving manual
selection/order, edits, copies, versions, `READY`, archive/restore, and stale-
output protections.

Shared Build Week traffic is guarded by `demo-shared`, which accepts only
seeded or explicitly marked demo profiles and rejects obvious personal
identifiers before a provider request. The fictional Maya Chen fixture is the
only intended live-smoke input. See
[29-GPT-5.6-Application-Writing-Intelligence.md](29-GPT-5.6-Application-Writing-Intelligence.md)
and [30-Build-Week-Demo-Data-and-Privacy.md](30-Build-Week-Demo-Data-and-Privacy.md).
Sprint 14.1.2 replaces fixed snippet-count assumptions with structured
application questions and answers keyed by `question_id`. Every supplied
required question must receive exactly one non-empty answer in input order;
optional unanswered questions may be omitted, and zero questions permits zero
snippets. A missing required answer is eligible for one targeted answer-only
repair that preserves valid resume and cover-letter sections. Claim/evidence
validation and the `private`/`demo-shared` policy remain unchanged. No live
request was run for Sprint 14.1.2, and live OpenAI acceptance remains pending.

## What is not built yet

The product has a complete approved-memory-to-application-package path, but it
does **not** yet include:

- guided career interviewing that fills memory gaps conversationally;
- source-aware figure, table, slide, or OCR understanding;
- a seeded, one-click showcase/demo mode;
- package-version-linked application outcomes, submission tracking, and a
  complete follow-up timeline;
- DOCX/PDF application-package export, visual resume templates, or ATS
  guarantees;
- browser-extension extraction or autofill;
- production authentication, multi-user operations, hosted exports, or public
  portfolio publishing.

Those omissions are deliberate. The implemented builder uses copy-ready drafts
and human review rather than treating document polish or submission automation
as a substitute for trustworthy proof.

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
- Application-package requirement detection and composition are bounded,
  deterministic heuristics. Positive-capability matching excludes negated
  limitations. Saved edits retain server-owned provenance and are audited for
  unsupported numbers, recognized capability claims, and cross-memory resume
  borrowing; unresolved blocking warnings prevent readiness.
- Outcome data is sparse and is never treated as proof of causality.
- The current local experience is development-oriented; deployment, security,
  and operational hardening need their own scoped work before broad use.

## What to build next

Sprint 15 should add an **Intelligent Guided Career Interview** that asks the
smallest useful questions when compiled proof is thin and routes every factual
answer through review. Richer exports, seeded demo data, and package tracking
remain subsequent MVP work.

See [25-Roadmap-to-MVP.md](25-Roadmap-to-MVP.md) for the sequence,
[14-Resume-Cover-Letter-Builder.md](specs/14-Resume-Cover-Letter-Builder.md) for
the implemented Sprint 14 contract, and
[28-Application-Package-Builder.md](28-Application-Package-Builder.md) for the
workflow guide.
