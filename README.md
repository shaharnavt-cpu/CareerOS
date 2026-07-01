# CareerOS

CareerOS is an AI-powered career operating system that remembers a user's
professional journey, reduces repetitive work, and provides evidence-based
recommendations while keeping the user in control.

The project is currently in **Sprint 1: Project Foundation**. The repository
contains runnable frontend and backend shells, but no CareerOS business logic.

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

Optionally copy `.env.example` to `.env` when local configuration is needed.

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
