# CareerOS

CareerOS is a career-intelligence system that turns reviewed professional
evidence into reusable, role-specific proof while keeping the user in control.
It currently includes evidence listening and review, canonical career memory,
project enrichment, compiled memory profiles, diagnosis, proof artifacts, and
application intelligence with a key-free deterministic path. Sprint 14 adds a
versioned Application Package Builder that creates evidence-traced positioning,
resume bullets, a cover letter, answers matched to explicitly supplied
application questions, proof suggestions, and unsupported-claim warnings from
explicitly selected approved memory. Sprint
14.1 adds a provider boundary with improved local writing and an optional
GPT-5.6 Responses API path while keeping validation and persistence server-owned.

For the current product snapshot, MVP roadmap, intelligence boundaries, and
Windows development handoff, begin with
[docs/00-Current-State.md](docs/00-Current-State.md),
[docs/25-Roadmap-to-MVP.md](docs/25-Roadmap-to-MVP.md),
[docs/26-Intelligence-Architecture.md](docs/26-Intelligence-Architecture.md),
[docs/27-Claude-Code-Handoff.md](docs/27-Claude-Code-Handoff.md), and
[docs/28-Application-Package-Builder.md](docs/28-Application-Package-Builder.md).
The GPT-5.6 path and Build Week data rules are documented in
[docs/29-GPT-5.6-Application-Writing-Intelligence.md](docs/29-GPT-5.6-Application-Writing-Intelligence.md)
and [docs/30-Build-Week-Demo-Data-and-Privacy.md](docs/30-Build-Week-Demo-Data-and-Privacy.md).

## Current application-package flow

Open <http://localhost:3000/application-packages> after starting the local
stack. Create or reopen a target package, select approved Career Memory, and
generate a reviewable draft. Target text changes relevance only; factual output
comes from each exact selected memory and its approved same-memory enrichment.
Outcome feedback remains strategy-only.

Generated, regenerated, and saved user edits append immutable versions. Target,
selection, or compiled-proof changes make the latest output stale; stale output
must be regenerated before it can be marked ready or saved as a current edit.
Blocking claim warnings also prevent readiness. Edit provenance remains
server-owned, warnings and complete direct-source traces stay visible, and
generated prose never overwrites the user's base resume or canonical memory.

The backend API is rooted at `/api/application-packages`; interactive contracts
are available in FastAPI's local `/docs`. Deterministic package generation does
not require an external model key. OpenAI generation is explicit, server-side,
and followed by the same deterministic validation. Copy-ready output is
implemented; automatic submission and PDF/DOCX/ATS guarantees are not.

## Repository layout

```text
CareerOS/
├── frontend/             Next.js web application
├── backend/              FastAPI service
├── browser-extension/    Future Plasmo extension
├── shared/               Future shared contracts and types
├── prompts/              Future versioned AI prompts
├── templates/            Future document templates
├── scripts/              Future development utilities
├── tests/                Future cross-application tests
├── assets/               Shared project assets
└── docs/                 Product and architecture documentation
```

## Prerequisites

- Git
- Node.js 20.9 or newer
- npm 10 or newer
- Python 3.12
- Docker Desktop or another Docker Compose-compatible runtime

## Initial setup

Install the frontend dependencies from the repository root:

```bash
npm install
```

Create a Python virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".\backend[dev]"
```

On macOS or Linux, activate the environment with:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e "./backend[dev]"
```

Create the local environment file from the committed template:

```powershell
Copy-Item .env.example .env
```

On macOS or Linux:

```bash
cp .env.example .env
```

The default values are for local development only. They configure both Docker
Compose and the backend to use PostgreSQL at `localhost:5432`.
They also select deterministic local reasoning and
`APPLICATION_WRITER_PROVIDER=local-deterministic`, so document and application-
package workflows complete without an external LLM API key. The existing
listening/reasoning provider uses `REASONING_PROVIDER`, while application
writing is configured independently with the `APPLICATION_WRITER_*` and
`OPENAI_APPLICATION_*` variables in `.env.example`.

For one approved Build Week smoke, enter `OPENAI_API_KEY` manually in the
untracked `backend/.env` (which overrides the supported repository-root
`.env`), select `APPLICATION_WRITER_PROVIDER=openai` and
`APPLICATION_WRITER_DATA_POLICY=demo-shared`, and set
`RUN_LIVE_OPENAI_TESTS=true`. Keep the Sol review disabled for the cost-safe
Terra smoke. Do not paste or commit a key. The exact gated command is:

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.live_application_writer_smoke
```

Sprint 14.1.2 aligns answers to a structured question list by `question_id`;
required questions receive exactly one non-empty answer, optional unanswered
questions may be omitted, and an empty question list produces no snippets. A
missing required answer can trigger one answer-only structural repair without
regenerating valid resume or cover-letter content. Factual-claim validation and
the private/`demo-shared` data boundary are unchanged. No live request was run
for Sprint 14.1.2, and live OpenAI acceptance remains pending.

## Local database

Start PostgreSQL 16 and wait for its health check to pass:

```bash
docker compose up -d --wait database
```

Apply all database migrations from the repository root:

```bash
python -m alembic -c backend/alembic.ini upgrade head
```

Inspect the container and migration state when needed:

```bash
docker compose ps
python -m alembic -c backend/alembic.ini current
```

## Run locally

Start the frontend from the repository root:

```bash
npm run dev:frontend
```

The web application is available at <http://localhost:3000>.

In another terminal with the virtual environment active, start the API:

```bash
python -m uvicorn app.main:app --app-dir backend --reload
```

The API is available at <http://localhost:8000>. Its health endpoint is
`GET http://localhost:8000/api/health`, and interactive API documentation is
available at <http://localhost:8000/docs>.

Stop the local database without deleting its data:

```bash
docker compose down
```

To also delete the local database volume and start from an empty database, run
`docker compose down --volumes`.

## Quality checks

```bash
npm run lint
npm run build
python -m pytest backend/tests
python -m ruff check backend
```

See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Product
direction lives in [docs/](docs/), and planned phases are summarized in
[ROADMAP.md](ROADMAP.md).
