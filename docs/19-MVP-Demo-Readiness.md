# MVP Demo Readiness

This script keeps the current CareerOS loop demoable without pretending the
browser extension exists yet.

## Run locally

1. Set local deterministic reasoning:
   `REASONING_PROVIDER=local-deterministic`
2. Start Postgres:
   `docker compose up -d`
3. Run migrations:
   `cd backend`
   `.venv\Scripts\activate`
   `python -m alembic upgrade head`
4. Start the backend:
   `uvicorn app.main:app --reload`
5. Start the frontend:
   `cd frontend`
   `npm run dev`

## Demo flow

1. Open `/onboarding`.
2. Upload or paste representative resume/transcript content.
3. Continue to `/review`.
4. Approve enough memories for the demo:
   - one education memory;
   - one project, preferably Gas Kinematics / morphology;
   - one experience, preferably Undergraduate Learning Assistant;
   - one technical skill set.
5. Open `/dashboard` and confirm:
   - approved canonical memory count is non-zero;
   - pending review count is visible;
   - evidence count is visible;
   - suggested actions link to review, stories, applications, and listening.
6. Open `/stories` and confirm approved memories appear as story ingredients or
   story proposals.
7. Open `/applications`.
8. Use the "Load analytics internship sample" button or paste:

```text
Data Analytics Intern

We are looking for a student intern to support data analysis, reporting, and
business insight generation. Responsibilities include cleaning data, using
Python or SQL to analyze datasets, creating summaries or visuals, and
communicating findings to non-technical stakeholders. Preferred qualifications
include experience with Excel, Python, SQL, analytics coursework, and project
experience translating data into recommendations.

Application question:
Tell us about a project or experience that prepared you for this analytics
internship.
```

Expected result:

- CareerOS detects Python, SQL, Excel, analytics, data analysis, and reporting.
- CareerOS matches approved memory only.
- Gas Kinematics should be selected as the primary memory when approved.
- Technical Skills should appear as supporting memory.
- Drafts are direct first-person answers with short, medium, and detailed
  variants.
- Copy and save controls work.

## Demo reset guidance

The dashboard can expose a developer-only "Reset local demo browser state"
control when `NEXT_PUBLIC_DEMO_TOOLS=true` or
`NEXT_PUBLIC_DEVELOPER_TOOLS=true`. It clears browser session/local state used
for onboarding convenience. It does not wipe PostgreSQL or approved Career
Memory.

To reset the database for a fully clean demo:

```powershell
docker compose down -v
docker compose up -d
cd backend
.venv\Scripts\activate
python -m alembic upgrade head
```

## Known limitations

- The browser extension is intentionally out of scope.
- Story intelligence is still early; the workspace should show ingredients and
  proposals clearly, but story generation is not final.
- Local deterministic reasoning is intentionally transparent and template-based.
- Application drafts are editable starting points, not final submissions.
