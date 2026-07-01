# CareerOS

CareerOS is an AI-powered career operating system that remembers a user's
professional journey, reduces repetitive work, and provides evidence-based
recommendations while keeping the user in control.

The project currently includes the project foundation and Career Knowledge
Engine persistence layer.

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
