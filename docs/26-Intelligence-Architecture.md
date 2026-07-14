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
  -> Diagnosis / Proof Artifact / Resume / Cover Letter / Applications
```

The last three document-oriented consumers are outputs. The durable career
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
profile should remain factually stable when the target role changes.

## How Sprint 14 should use this architecture

The Resume and Cover Letter Builder should be a consumer of the intelligence
layer, not a bypass around it:

1. parse target job/application text into relevance context;
2. select approved memories and compile project profiles for that target;
3. use existing proof artifacts and diagnosis to choose the strongest safe
   positioning;
4. generate claim ingredients and prose only from supported compiled fields;
5. expose an evidence trace and warnings for each material claim;
6. let the user edit/review before saving a package snapshot; and
7. store later feedback as an outcome signal, never as retroactive proof.

This preserves the product's advantage: CareerOS remembers and reasons about
the user's approved work before it writes about it.

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
