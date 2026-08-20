# Build Week Demo Data and Privacy

## Purpose

The shared CareerOS Build Week Demo API project is restricted to fictional,
synthetic, or explicitly redacted data. CareerOS enforces this on the server;
prompt instructions are not the security boundary.

## Data policies

`APPLICATION_WRITER_DATA_POLICY` accepts two modes:

| Policy | Permitted use | Deterministic rule |
| --- | --- | --- |
| `private` | Normal approved CareerOS memory with a non-shared API project | Minimize context and exclude unrelated, rejected, proposed, duplicate, and archived material. |
| `demo-shared` | Seeded or explicitly marked demo profiles only | Reject normal personal profiles and obvious personal identifiers before an OpenAI request. |

`demo-shared` rejects phone numbers, real-looking email addresses, street
addresses, API-key patterns, and other restricted personal identifiers. A
rejection is actionable: use the fictional fixture, redact and explicitly mark
demo data, or switch to an appropriate non-shared project under `private`.

Neither mode permits secrets in prompts or persistence. The browser never
receives `OPENAI_API_KEY`; requests use `store=false`; full prompts, raw private
career context, authorization headers, and hidden reasoning are not logged.

## Fictional fixture

The Build Week fixture uses **Maya Chen**, a fictional MS Analytics student
applying for a fictional Data Science Intern role. It contains synthetic:

- a scientific-data research project with approved analytical, modeling,
  uncertainty, and communication evidence;
- an image-categorization/data-quality project with approved inspection,
  labeling, categorization, and review-workflow evidence;
- peer-teaching experience as communication proof;
- approved enrichment and provider-ready compiled-memory snapshots;
- proof artifacts and traceable source references; and
- deliberate missing direct proof for concrete technologies so grouped
  unsupported/do-not-claim behavior remains visible.

Its application package supplies exactly these three required questions in
this order:

1. `motivation` — Why are you interested in this Data Science internship?
2. `complex-data-project` — Describe a project where you analyzed complex data.
3. `quality-reliability` — Describe how you ensured the quality or reliability
   of your work.

Each answer keeps its question ID and fictional evidence references. No generic
questions are added to reach a fixed answer count.

The fixture contains no Arnav personal data, real email address, phone number,
street address, private application history, raw uploaded document, Gmail or
calendar content, or API key. It is rich enough to demonstrate memory ranking,
semantic requirement matching, claim planning, natural drafting, evidence
references, missing proof, and the deterministic provider contract. Separate
package integration fixtures verify 2-4 recommendations, persistence, grouped
warnings and evidence, and saved provider metadata.

## Build Week operating procedure

Before a live smoke:

1. keep all mock/local checks passing without a key;
2. enter the key manually into the untracked `backend/.env` or process
   environment; the supported repository-root `.env` is loaded first and
   `backend/.env` overrides it for backend-only values;
3. set `APPLICATION_WRITER_PROVIDER=openai`;
4. set `APPLICATION_WRITER_DATA_POLICY=demo-shared`;
5. keep `OPENAI_APPLICATION_ENABLE_REVIEW_PASS=false`;
6. set `RUN_LIVE_OPENAI_TESTS=true`; and
7. confirm the smoke uses only the seeded Maya Chen fixture.

During the smoke, make exactly one compact Terra call. Do not print the secret,
authorization header, or full prompt. Report only provider/model, latency,
available token counts, deterministic validation status, and PASS/FAIL. Sol is
optional only after separate explicit approval. After testing, return
`RUN_LIVE_OPENAI_TESTS=false`; retaining a key in the untracked local file is a
user decision.

No live provider request was run for Sprint 14.1.2. Live OpenAI acceptance of
the explicit question/answer contract remains pending.
