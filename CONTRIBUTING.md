# Contributing to CareerOS

Thank you for helping build CareerOS. Read the files in `docs/` before making
architectural or product changes. Accepted architecture decisions remain in
force until they are explicitly revised.

## Development workflow

1. Start from an up-to-date `main` branch.
2. Create a focused branch such as `feature/short-description` or
   `fix/short-description`.
3. Keep changes small and aligned with the current sprint.
4. Add or update tests for behavior changes.
5. Run all relevant quality checks before opening a pull request.
6. Explain the problem, approach, verification, and follow-up work in the pull
   request description.

Do not commit secrets, local environment files, virtual environments,
dependency directories, or generated build output.

## Coding standards

### TypeScript and React

- Use TypeScript in strict mode.
- Prefer Server Components unless browser-side state or APIs require a Client
  Component.
- Keep components focused and use descriptive names.
- Run ESLint and the production build before requesting review.
- Use npm and commit `package-lock.json`; do not introduce another JavaScript
  package manager without an architecture decision.

### Python and FastAPI

- Target Python 3.12 and add type hints to public functions.
- Keep HTTP routing in `backend/app/api/` and business capabilities in
  `backend/app/services/`.
- Keep configuration and cross-cutting infrastructure in `backend/app/core/`.
- Format and lint with Ruff.
- Test API behavior with pytest and FastAPI's `TestClient`.

### General

- Prefer deterministic logic over AI where deterministic logic is sufficient.
- Do not add authentication, AI, database, or integration code without an
  approved sprint scope.
- Keep modules explicit and avoid hidden coupling between applications.
- Document developer-facing behavior and non-obvious decisions.

## Commit and pull request guidance

Use concise, imperative commit subjects, optionally prefixed by an area:

```text
frontend: add application shell
backend: expose service health check
docs: clarify local setup
```

Pull requests should pass:

```bash
npm run lint
npm run build
python -m pytest backend/tests
python -m ruff check backend
```
