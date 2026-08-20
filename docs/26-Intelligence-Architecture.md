# CareerOS Intelligence Architecture

## The central idea

CareerOS separates what the user can factually claim from how that claim should
be framed for a target opportunity. The system's intelligence is the maintained
relationship between evidence, approval, enrichment, compiled interpretation,
and generated materials.

```text
Raw Evidence
  -> Review Proposal
  -> Approved Canonical Memory
  -> Approved Enrichment
  -> Compiled Memory Profile
  -> Diagnosis / Proof Artifact / Application Intelligence / Application Package
```

These downstream consumers are interpretations and outputs. The durable career
memory and its approved provenance remain the source of truth.

## The layers

| Layer | What it contains | Can support factual claims? | Durable? |
| --- | --- | --- | --- |
| Raw evidence | Source excerpts, uploads, pasted text, and source metadata | Not until reviewed | Yes |
| Review proposal | A candidate interpretation of source material | No | Yes |
| Approved canonical memory | User-approved career fact or project identity | Yes | Yes |
| Approved enrichment | Reviewed detail attached to one canonical memory | Yes, for that exact memory | Yes |
| Compiled memory profile | Deterministic, current interpretation of approved layers | Yes, as a derived view of those layers | No; compile-on-read |
| Diagnosis/proof/application package | Role- and opportunity-specific use of the compiled profile | Only where its claim traces back to approved layers | Yes as a snapshot when saved |
| Outcome signal | Approved feedback about what happened or what framing helped | No; strategy only | Yes |

## Evidence, memory, and enrichment

### Raw evidence

Evidence is the source material CareerOS can point to: a resume excerpt, a
project note, a document section, or a user-provided answer. Evidence keeps a
source label, excerpt, confidence, and ownership context.

Evidence is not automatically a fact. It must first pass through a reviewable
proposal and user decision.

### Canonical Career Memory

Canonical memory is the durable, user-approved representation of a career fact,
project, experience, skill set, education record, program, or achievement. It
has an identity, title, structured fields, linked evidence IDs, source IDs, and
the review decision that made it eligible.

Canonical memory is the base factual boundary. It should not be overwritten by
generated prose, diagnosis, or target-role language.

### Project Evidence Enrichment

Enrichment attaches deeper source-backed detail to an existing approved memory:
methods, inputs, findings, limitations, outputs, or context that a short resume
line cannot carry.

An enrichment is eligible only when:

1. it belongs to the current user;
2. it points to the exact selected canonical memory ID; and
3. its status is `APPROVED`.

`PROPOSED`, `REJECTED`, and `ARCHIVED` enrichments are review history, not active
factual input. Approval can rebuild a compatibility projection on the canonical
record, but downstream intelligence should use the approved enrichment records
through the compiler rather than treating that projection as a separate source
of truth.

## Identity resolution and duplicate prevention

CareerOS uses deterministic identity resolution to avoid creating multiple
project memories for the same work. It considers stable title phrases, evidence
themes, structured fields, time/context overlap, pending proposals, and an
explicit user selection.

Possible outcomes include creating a new memory, enriching an existing memory,
flagging a possible merge, retaining quiet supporting evidence, or asking for
confirmation.

Two rules matter more than a high match score:

- CareerOS never automatically merges canonical memories.
- Once a caller selects a `memory_id`, that exact ID is authoritative. Identity
  matching cannot redirect proof generation or borrow another project's facts.

Direct duplicate enrichment submission is also handled explicitly. If the same
structured evidence is already proposed or approved for the selected memory,
the API returns a structured `409 DUPLICATE_ENRICHMENT`. The workspace preserves
the pasted input, displays a visible warning, and keeps/highlights the existing
record instead of creating another one.

## Career Memory Compiler

The Career Memory Compiler is the interpretation layer between approved memory
and downstream intelligence. It compiles one selected memory at read time using
only eligible inputs and returns a `CompiledCareerMemoryProfile`.

The profile can contain:

- project boundary and aliases;
- research problem, data/inputs, methods, tools, workflow steps, findings,
  limitations, outputs, and context;
- supported skills and safe claim ingredients;
- role relevance and a target-role interpretation;
- warnings and missing/weak sections;
- resolved evidence references, approved enrichment IDs, approved outcome-signal
  IDs, confidence, and compiler version.

The profile is deliberately not a new database truth. It is regenerated from
the current approved layers. A saved proof artifact stores the profile/provenance
used for that version so historical material remains inspectable.

### Deterministic intelligence, not invented detail

Compiler patterns are bounded. A project-specific term appears only when it is
present in approved canonical material, linked evidence, or approved enrichment
for the selected project. If coverage is weak, the compiler emits missing
evidence language rather than strong role claims.

This supports rich project understanding where approved evidence exists while
keeping sparse projects honest.

### Project boundaries: Gas Kinematics and UNICORN

Gas Kinematics and UNICORN are a regression-critical example of identity
discipline.

| Selected memory | Eligible factual detail | Detail that must stay out |
| --- | --- | --- |
| Gas Kinematics | Approved spectroscopy/imaging, H-alpha, GALFIT, uncertainty, quality-control, and morphology evidence | UNICORN image inspection, categorization, t-SNE, and labeling evidence |
| UNICORN | Approved image/FITS inspection, detection review, categorization, t-SNE, data-quality, and documentation evidence | Gas H-alpha, `[NII]`, CEERS/RUBIES, GALFIT, `sigma_gas`, and morphology evidence |

The compiler can retain a boundary warning internally, but generated prose
should describe the selected project's work rather than carrying the other
project's terminology into its case study.

## Diagnosis

Career Diagnosis reads approved memory and compiled project facts to explain
where proof is strong, thin, hard to recognize, or mismatched to a target. It
recommends a focused proof sprint rather than treating a lack of evidence as a
lack of ability.

Diagnosis should surface gaps such as missing methods, outputs, quantified
results, or target relevance. It must not create factual claims simply because a
job description rewards a skill.

## Proof artifacts

Proof Artifact Builder packages one selected approved memory into a role-aware,
versioned work sample. It uses the compiled profile as its primary factual input
and preserves evidence/enrichment/signal provenance in the generated snapshot.

The artifact builder converts structured facts into clean prose instead of
dumping raw resume text into a Problem section. It also adds warnings, readiness,
and target-aware reviewer questions.

Artifact freshness is part of trust: changing memory, target role, artifact
type, or channel invalidates the visible saved preview. The UI moves to a
new-draft state and asks the user to generate a new artifact for the selected
memory instead of showing stale content under a different selection.

## Application packages

The Sprint 14 Application Package Builder compiles every explicitly selected
approved memory independently, ranks the resulting profiles for a target, and
creates a structured positioning summary, resume bullets, cover letter,
answers for explicit application questions, and proof-artifact suggestions. It does not query raw
records broadly to assemble prose, and it does not use a target posting as a
career fact.

Application-package persistence deliberately separates a mutable workspace from
append-only versions:

- the package parent stores the current target fields, selected memory IDs, and
  `DRAFT`/`READY`/`ARCHIVED` status;
- every generation, regeneration, and saved edit appends a version containing
  target and compiled-profile snapshots, outputs, traces, warnings, claim
  ledger, IDs used, edit metadata, and generator version; and
- an input fingerprint makes output stale when the target, selection, or
  current compiled proof changes. Stale output cannot be marked ready or saved
  as a current edited version, and a latest version with a `BLOCKING` warning
  cannot be marked ready.

The trace system keeps five roles distinct: direct approved-memory proof,
direct approved-enrichment proof, inferred role-aware framing backed by that
proof, strategy-only outcome signals, and relevance-only target context.
Per-surface claim-ledger entries record factual references, support level,
strategy references, edit state, and warnings for positioning, bullets, letter
content, and snippets. Generated claim traces retain every approved direct
source in the applicable compiled profile.

User edits create another immutable version and are marked for review. The
service accepts nested output payloads for compatibility but merges only allowed
text; provenance IDs, traces, confidence, and claim metadata stay server-owned.
Only changed claims become `user_review_required`, and their ledger entries do
not certify preserved traces with factual IDs. The saved-edit audit compares
resume wording with its exact memory, detects cross-memory borrowing, ignores
negated/limitation clauses as support, and emits `BLOCKING` warnings for
unsupported numbers or recognized capabilities. Audit findings are recomputed
so corrected edits can clear them.

## Sprint 14.1 writing-provider boundary

Sprint 14.1 inserts a typed provider boundary after approved evidence has been
compiled, filtered, semantically ranked, and narrowed to the best 2-4 memories.
The provider returns structured job understanding, coverage, claim plans,
drafts, evidence references, and concise review notes. Persistence still occurs
only after CareerOS revalidates claims, tools, metrics, memory boundaries,
strategy labels, target-only context, and excluded-record rules.

`local-deterministic` and `openai` implement the same contract. The OpenAI
adapter uses the Responses API, strict Structured Outputs, `store=false`, and
server-held configuration. This seam can accept a future Anthropic provider
without letting any provider own compilation, policy, readiness, or versioning.
Provider failure cannot remove prior versions or create an empty version.

The data-policy check is also server-owned. `private` allows minimized approved
user context for a suitable non-shared project. `demo-shared` admits only seeded
or explicitly marked demo profiles and rejects obvious identifiers before a
request. See [29-GPT-5.6-Application-Writing-Intelligence.md](29-GPT-5.6-Application-Writing-Intelligence.md)
and [30-Build-Week-Demo-Data-and-Privacy.md](30-Build-Week-Demo-Data-and-Privacy.md).

### Sprint 14.1.2 question/answer boundary

The writing input contains an ordered `application_questions` list. Each item
has `question_id`, `question_text`, `required`, optional `maximum_length`,
optional `response_type`, and `relevant_target_requirement_ids` when applicable.
The provider therefore never infers an answer count or invents generic prompts.
Returned application answers map to that list by `question_id`; deterministic
validation enforces required coverage, known and unique IDs, non-empty required
answers, and input order. Optional unanswered questions may be absent, and an
empty question list requires an empty snippet list.

A missing required answer is a structural failure, not a hallucination. It is
eligible for one targeted provider repair containing only the missing question
IDs/text, already valid package sections, relevant evidence atoms, prohibited
claims, and the strict answer schema. Only repaired answers are merged before
the entire package is validated again; resume and cover-letter sections are not
regenerated. Unsupported tools, outcomes, or evidence references in a repaired
answer remain blocked by the unchanged Sprint 14.1.1 factual-claim gate. The
same `private`/`demo-shared` policy applies to generation and repair.

## Outcome signals

Outcome feedback may say that an artifact led to an interview, that a framing
was helpful, or that a target strategy should be repeated. It is useful for
future prioritization but does not prove a skill, metric, causal relationship,
or factual project result.

Only approved, current-user feedback linked to the selected memory can be
included, and it carries an explicit caveat such as "strategy signal, not proof
of causality." Archived feedback is excluded from current compilation.

## Target roles: relevance, not facts

Target job text and role names may change:

- which approved methods are emphasized;
- which reviewer question is asked;
- how a proof artifact is positioned; and
- which gap is most important to close.

They may not add a new job, leadership role, tool, dataset, project method,
metric, outcome, deployment claim, or conclusion. The same compiled factual
profile should remain factually stable when the target role changes. Capability
matching uses positive fields and token boundaries; a limitation such as "no
AWS was used" is not positive AWS support. Sparse profiles receive gap language,
not inferred technical capability.

## How Sprint 14 uses this architecture

The Application Package Builder is an implemented consumer of the intelligence
layer, not a bypass around it:

1. target job/application text becomes relevance-only context;
2. the user explicitly selects approved memories;
3. the service compiles each exact memory and ranks the approved profiles;
4. deterministic composition uses supported compiled fields only;
5. unsupported target requirements become warnings, unsupported claims, and
   reviewer questions;
6. direct proof, supported inferred framing, strategy-only signals, and
   target-only context remain separate in traces, while the claim ledger records
   the resulting source references, support, edits, and warnings; and
7. generated, regenerated, and edited states are preserved as immutable package
   versions without mutating Career Memory.

Existing proof artifacts inform suggestions only: `READY` can become `ATTACH`,
an unfinished non-archived artifact becomes `REVIEW`, and absence becomes
`BUILD`. Career Diagnosis is not silently imported as factual content. Later
package-linked feedback must remain an outcome signal, never retroactive proof.

This preserves the product's advantage: CareerOS remembers and reasons about
the user's approved work before it writes about it. See
[28-Application-Package-Builder.md](28-Application-Package-Builder.md) for the
implemented workflow and API.

## Non-negotiable implementation rules

- Preserve user ownership and exact-memory selection boundaries in every query.
- Use approved-only data for factual claims.
- Keep outcome signals, role interpretation, and unsupported claims distinct
  from proof.
- Prefer deterministic local behavior where it is sufficient.
- Make provenance inspectable in saved outputs.
- Treat missing evidence as a product prompt, not a text-generation failure.
- Add regression coverage whenever a consumer could leak one memory's details
  into another.
