# Claude Code Handoff

## Purpose

This is the practical starting point for the next implementation task. CareerOS
already has an approved-memory, enrichment, compiler, diagnosis, proof-artifact,
and application-intelligence foundation. The next planned feature is the
reviewed Resume and Cover Letter Builder described in
[14-Resume-Cover-Letter-Builder.md](specs/14-Resume-Cover-Letter-Builder.md).

Read these documents before changing product behavior:

1. [00-Current-State.md](00-Current-State.md)
2. [25-Roadmap-to-MVP.md](25-Roadmap-to-MVP.md)
3. [26-Intelligence-Architecture.md](26-Intelligence-Architecture.md)
4. [13.1-Career-Memory-Compiler-Proof-Intelligence.md](specs/13.1-Career-Memory-Compiler-Proof-Intelligence.md)
5. [14-Resume-Cover-Letter-Builder.md](specs/14-Resume-Cover-Letter-Builder.md)

## Repository orientation

| Location | Responsibility |
| --- | --- |
| `backend/app/` | FastAPI routes, domain services, schemas, persistence models, and deterministic reasoning. |
| `backend/migrations/` | Alembic migration revisions. |
| `backend/tests/` | Backend unit, API, compiler, and migration regression coverage. |
| `frontend/app/` | Next.js pages and route-level UI. |
| `frontend/components/` | Product components and feature workspaces. |
| `frontend/lib/` | API client, types, and frontend helpers. |
| `frontend/__tests__/` | Frontend component and integration tests. |
| `docs/specs/` | Versioned product and technical specifications. |
| `.env.example` | Local-development defaults; copy it, do not commit a real `.env`. |

The repository is a modular monolith: Next.js + TypeScript frontend, FastAPI +
SQLAlchemy backend, PostgreSQL 16, and Alembic migrations. Local deterministic
reasoning is a supported first-class path; do not require a model key to run
the core workflow.

## First-time Windows CMD setup

Open **Command Prompt** and replace `<repository-url>` only when cloning a
fresh checkout. These commands are intentionally CMD commands, not PowerShell.

```cmd
git clone <repository-url> CareerOS
cd /d CareerOS
copy .env.example .env
docker compose up -d --wait database
npm install
cd backend
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m alembic upgrade head
cd ..
```

If the repository is already present, start at its absolute path instead:

```cmd
cd /d C:\path\to\CareerOS
copy .env.example .env
docker compose up -d --wait database
npm install
cd backend
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m alembic upgrade head
cd ..
```

Do not overwrite an existing local `.env` without checking it first. The
committed example uses local PostgreSQL and `REASONING_PROVIDER=local-deterministic`.

## Run the local stack

Start or confirm the database:

```cmd
cd /d C:\path\to\CareerOS
docker compose up -d --wait database
docker compose ps
```

Run the backend in one Command Prompt:

```cmd
cd /d C:\path\to\CareerOS\backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Run the frontend in a second Command Prompt:

```cmd
cd /d C:\path\to\CareerOS\frontend
npm run dev
```

Use `http://localhost:3000` for the web app and
`http://localhost:8000/docs` for FastAPI's local API docs. The backend health
endpoint is `http://localhost:8000/api/health`.

## Required verification

Run the complete verification sequence after a backend or frontend feature.
Run it from a clean enough working tree that failures can be attributed to the
task.

```cmd
cd /d C:\path\to\CareerOS\backend
.venv\Scripts\python.exe -m ruff check app migrations tests
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m alembic current
.venv\Scripts\python.exe -m alembic check
cd /d C:\path\to\CareerOS\frontend
npm run lint
npm run typecheck
npm test
npm run build
```

For a documentation-only change, use the lighter scope audit:

```cmd
cd /d C:\path\to\CareerOS
git diff --check
git status --short
git diff --name-only
```

Never mask a failing check. Fix it or record the exact pre-existing blocker
before asking for a decision.

## Branch and commit workflow

Start a scoped feature branch from the current base only after inspecting the
worktree:

```cmd
cd /d C:\path\to\CareerOS
git status --short --branch
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c feature/sprint-14-resume-cover-letter-builder
```

Before committing, review the intended scope and staged patch:

```cmd
cd /d C:\path\to\CareerOS
git status --short
git diff --stat
git diff --check
git add backend frontend docs
git diff --cached --check
git diff --cached --stat
git commit -m "feat: add reviewed resume and cover letter builder"
git push -u origin feature/sprint-14-resume-cover-letter-builder
```

Use narrower `git add` paths when a task does not touch all three areas. Do
not use destructive reset or checkout commands to clear somebody else's local
work. Do not commit `.env`, logs, virtual environments, generated coverage, or
temporary smoke-test output.

## Intelligence rules: do not break these

1. **Review gates facts.** Raw evidence and proposals are not factual support
   until the user approves them into canonical memory or approved enrichment.
2. **The selected memory ID is authoritative.** A fuzzy identity match may
   suggest an action; it cannot redirect a consumer to a different memory.
3. **Keep projects separate.** Gas Kinematics and UNICORN are the regression
   pair. No title, tool, evidence, or enriched detail may cross their boundary.
4. **Use compiled memory for downstream factual content.** A proof artifact or
   new document consumer must read the selected approved memory through the
   compiler; it must not reassemble facts from broad user-level queries.
5. **Approved-only enrichment.** Proposed, rejected, archived, foreign, and
   unlinked enrichment is excluded from the compiled profile.
6. **Duplicate prevention is a user-visible workflow.** A duplicate enrichment
   is a structured conflict and an actionable UI warning, not a silent failure.
7. **Keep stale output honest.** Changing selected memory, target, output type,
   or relevant input must clear the old preview or explicitly mark a new draft.
8. **Outcome feedback is a signal, not proof.** It can influence strategy or
   prioritization, never create a factual skill, result, or causality claim.
9. **Target relevance is not evidence.** A job description may choose emphasis
   and questions; it cannot add tools, metrics, scope, or achievements.
10. **Expose uncertainty.** Missing evidence should produce a gap, warning, or
    question, never plausible invented prose.

## Recommended Sprint 14 delivery shape

Treat [the Sprint 14 spec](specs/14-Resume-Cover-Letter-Builder.md) as the
source of scope. Deliver vertical slices in this order:

1. define package and immutable-version contracts/migrations;
2. build a deterministic claim-selection and provenance service using compiled
   profiles;
3. expose package generation/read APIs with ownership and stale-input checks;
4. build the reviewed package workspace with claim traces and warnings;
5. add regression tests for selected-memory, Gas/UNICORN, sparse evidence, and
   outcome-signal boundaries;
6. run the full verification sequence and one realistic local smoke path.

Do not start with templates, PDF polish, model integrations, job-board
automation, or browser autofill. They are consumers of a trustworthy package,
not substitutes for it.

## Handoff checklist

Before reporting a feature complete:

- [ ] Re-read the current spec and relevant prior specs.
- [ ] Inspect `git status --short --branch` before and after the work.
- [ ] Confirm migration state with `alembic upgrade head`, `current`, and
      `check` when schema changes.
- [ ] Add regression coverage for every factual-boundary or stale-output risk.
- [ ] Run lint, type checks, tests, and build for code changes.
- [ ] Perform a small local UI/API smoke path with local deterministic mode.
- [ ] Inspect `git diff --check` and the staged diff before committing.
- [ ] Report the branch, commit hash, migrations, checks, any limitation, and
      final git status. Do not merge unless explicitly asked.
