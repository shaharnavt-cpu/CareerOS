# Career Diagnosis Engine

## What Career Diagnosis is

Career Diagnosis is CareerOS's first strategic judgment workspace. It compares a
target role or program with the user's approved Career Memory and produces a
compact diagnosis brief rather than a chat response or generic encouragement.

The brief answers:

- which career identity has the strongest current evidence;
- which approved memories and evidence references support that identity;
- what an evaluator may fail to recognize;
- which proof is missing or poorly packaged;
- which one seven-day proof sprint has the highest leverage;
- which low-leverage work should be deferred;
- which outreach and application messages to use next.

Diagnosis runs are persisted in `diagnosis_sessions` and `diagnosis_results`.
Rerunning a session recomputes its derived result from current approved memory
without mutating Career Memory, applications, drafts, or feedback history.

## Approved-memory trust boundary

Trusted claims come only from `canonical_memory_records`, the durable projection
created by an explicit approval decision. Pending, rejected, and otherwise
unapproved review proposals are not queried by the diagnosis engine.

Each Evidence Map entry preserves the canonical memory ID, memory type, title,
confidence, evidence IDs, relevant themes, evidence strength, and a concise
reason code. Target text and frustration context can change relevance ordering,
but the interface and response contract explicitly state that those inputs are
not proof.

If no approved Career Memory exists, CareerOS returns the durable empty state:
"Approve career memories before running a full diagnosis." It directs the user
to approve sourced memory before CareerOS attempts a career identity judgment.

## Recognition Gap

A Recognition Gap is the difference between the direction the user wants, what
approved memory can currently prove, and what an evaluator is likely to notice
from the current presentation. It is a proof or framing diagnosis, not a
judgment about ability or worth.

The deterministic v0 engine checks for bounded patterns such as:

- research or academic analysis that lacks business-facing framing;
- relevant skills without an inspectable portfolio artifact;
- AI interest without deployable product proof;
- leadership evidence that is not connected to the target;
- experiences that lack an outcome, validator, or role-specific implication.

The engine distinguishes evidence strength from overall diagnosis confidence
and says when proof is limited instead of inventing certainty.

## Proof Sprint

A Proof Sprint is one seven-day intervention built around the strongest existing
approved memory. It includes an objective, three to five sequenced actions, a
definition of the expected artifact, why the artifact matters, the memory and
evidence it strengthens, and how to use it in applications or outreach.

The default bias is to package strong existing proof before starting another
project. For analytics targets, the artifact is commonly a one-page case study
with a problem, method, visual, finding, and decision implication. For AI or
automation targets, it may be a concise README and short demo.

## Teach CareerOS

Teach CareerOS stores lightweight user learning in `career_feedback_events`.
The deterministic parser classifies notes as:

- `ARTIFACT_SUCCESS`;
- `APPLICATION_OUTCOME`;
- `DRAFT_FEEDBACK`;
- `POSITIONING_RULE`;
- `MEMORY_USAGE_RULE`;
- `GENERAL_LEARNING`;
- `UNKNOWN`.

Events begin as `PROPOSED` unless explicitly created otherwise. The user can
approve them as guidance or archive them. Obvious approved-memory references
are linked by ID, and optional application opportunity and draft links preserve
future outcome context.

Teach CareerOS events remain user-reported learning inputs. Approval lets a
future diagnosis use them for framing, but it does not convert them into
canonical factual proof or rewrite a historical application. Artifact success
summaries explicitly avoid claiming that one draft caused an outcome.

## Local deterministic behavior

The implementation is provider-neutral at the API boundary and currently uses
`local-deterministic-v0`. It does not call an LLM and requires no API key. Theme
detection, evidence ranking, identity selection, Recognition Gap rules, Proof
Sprint planning, messages, and feedback parsing are deterministic.

The API endpoints are:

- `POST /api/diagnosis/sessions`;
- `GET /api/diagnosis/sessions`;
- `GET /api/diagnosis/sessions/{id}`;
- `POST /api/diagnosis/sessions/{id}/rerun`;
- `POST /api/diagnosis/feedback-events`;
- `GET /api/diagnosis/feedback-events`;
- `PATCH /api/diagnosis/feedback-events/{id}`.

The frontend workspace is `/diagnosis`. It is linked from the global workspace
navigation and from Dashboard when approved memory exists.

## Limitations

- Vocabulary rules cannot understand every role family or ambiguous memory.
- Recognition likelihood is an inference, not an employer prediction.
- User-reported feedback is not statistically aggregated and cannot establish
  causality.
- v0 stores structured evidence references but is not the full Evidence Graph.
- The service uses the current demo user boundary until authentication becomes
  tenant-aware.
- Exact messages are drafts for user review; CareerOS does not send outreach or
  submit applications.

## Future outcome-learning plan

Future work can link immutable application, outreach, interview, artifact, and
project outcome events to the diagnosis and proof sprint that preceded them.
Longitudinal analysis should compare strategies only after enough observations
exist, preserve submission snapshots, distinguish correlation from causation,
and let users correct or delete learning inputs. A graph-backed version can then
connect Experience → Skills → Claims → Proof → Validators → Targets → Outcomes
without weakening the approved-memory trust boundary.
