# CareerOS Roadmap to MVP

## MVP thesis

CareerOS reaches MVP when one person can turn their approved career memory into
a truthful, opportunity-specific application package faster than they could
manually, while still seeing what supports every important claim and what is
missing.

The MVP is not defined by a long feature list. It is defined by one dependable
loop:

```text
Bring in experience -> approve it -> enrich it -> understand it ->
package it for an opportunity -> review it -> learn from the outcome
```

## Two useful MVP definitions

### Personal MVP: Arnav's daily use

CareerOS is personally useful when Arnav can:

1. ingest a resume, project note, or pasted experience without rebuilding the
   same story from scratch;
2. approve and enrich the career facts he is willing to claim;
3. paste a job description and see the strongest approved proof plus material
   gaps;
4. generate a tailored resume-bullet set, cover-letter draft, and application
   positioning summary with evidence traces and warnings;
5. review/edit the package before copying or exporting it; and
6. save what was used for the application and, in a later tracker, connect the
   exact package version to what happened afterward.

Personal MVP does not require browser autofill, external integrations, public
hosting, or automated submission.

### Demo MVP: collaborator, investor, or reviewer walkthrough

CareerOS is demo-ready when a new observer can complete a short, credible story
without the original builder explaining hidden context:

1. start with a recognizable source or seeded project;
2. show approved Career Memory and the evidence trail;
3. deepen the project with approved enrichment rather than a duplicate;
4. show the compiled profile or proof artifact adapting to a target role;
5. generate a reviewed application package with sources, warnings, and visible
   gaps; and
6. show that feedback informs later strategy without rewriting history.

The demo should make the distinction clear: CareerOS is a professional-memory
and proof system whose documents are outputs, not a generic chatbot producing
text on demand.

## Current progress toward MVP

| MVP capability | Status | Notes |
| --- | --- | --- |
| Capture evidence and source material | Implemented | Universal Listening and evidence extraction exist in deterministic local mode. |
| Review/approve durable career facts | Implemented | Canonical Career Memory is created from review decisions. |
| Avoid duplicate project memories | Implemented | Identity resolution and enrichment provide a reviewed alternative. |
| Deepen a project with methods/results | Implemented | Project Evidence Enrichment is approved separately from canonical memory. |
| Compile reliable project intelligence | Implemented | Career Memory Compiler creates an approved-only, selected-memory profile. |
| Diagnose proof and gaps | Implemented | Career Diagnosis uses approved memory; outcome feedback is strategy-only. |
| Generate reusable proof | Implemented | Proof Artifact Builder produces role-aware, versioned case studies. |
| Match opportunities and draft answers | Implemented | Application Intelligence matches approved memory and exposes gaps. |
| Tailored resume and cover letter | Implemented | Sprint 14.1 adds improved local writing and optional GPT-5.6 generation behind the same evidence and validation boundary. |
| Save a complete application package | Implemented | A package parent plus immutable generated, regenerated, and user-edited versions preserves target, profiles, outputs, traces, warnings, and IDs used. |
| Review and copy package output | Implemented | The workspace keeps drafts, warnings, evidence, unsupported claims, and copy controls together; readiness is blocked for stale output. |
| Guided memory-gap interview | Important next | Sprint 15 improves the quality of future proof. |
| Seeded Build Week data | Implemented | The fictional Maya Chen fixture exercises approved proof, missing-proof warnings, and the guarded live path. |
| Package-linked outcome tracking | Important next | Sprint 18 should connect a saved version to submission, follow-up, interview, and outcome history. |
| Browser extension/autofill | Deferred | Valuable only after the intelligence and package workflow are dependable. |

## Remaining must-haves

The approved-memory-to-saved-package loop now exists. These remaining items are
necessary for a rounded personal and demo MVP:

1. **Guided gap collection.** Ask the smallest useful questions when evidence is
   thin instead of producing weaker prose, and route factual answers through
   review.
2. **Practical file export.** Preserve reviewed package wording and warnings in
   a usable DOCX/PDF or similarly portable representation; copy controls are the
   current output path.
3. **Guided showcase UX.** Build Week now has safe fictional data; a later
   one-click walkthrough should guide a reviewer through it without setup.
4. **Package-linked application history.** Connect the exact saved version to
   submission, follow-up, interview, reflection, and outcome events without
   rewriting historical proof.

## Nice-to-have features

Do not let these distract from the complete loop above:

- visual resume templates and branded PDF/DOCX export;
- public portfolio pages;
- richer document/figure/table understanding;
- company research and market intelligence;
- email/calendar/drive integrations;
- full submission tracking and analytics dashboards;
- browser extraction and autofill;
- multi-user collaboration, external authentication hardening, and hosted
  operations;
- additional model providers or broader agentic workflows.

## Sprint 14 delivered and the next six sprints

### Sprint 14: Resume and Cover Letter Builder — delivered

CareerOS now has a reviewed Application Package Builder using exact selected
approved memory, approved same-memory enrichment, compiled profiles, and target
job context. It includes evidence traces, a claim ledger, warnings, copy-ready
output, staleness detection, and immutable package versions. Existing proof
artifacts are suggested as attach/review/build actions according to readiness
rather than imported as new facts. See
[the implemented specification](specs/14-Resume-Cover-Letter-Builder.md) and
[the workflow guide](28-Application-Package-Builder.md).

**Delivered outcome:** one target job produces a reviewable package containing
tailored bullets, a cover letter, positioning, answers for the supplied
application questions, proof suggestions, traces, warnings, unsupported claims,
and immutable versions without treating the job posting or outcome feedback as
factual proof.

### Sprint 14.1: GPT-5.6 Application Writing Intelligence — implemented, live smoke pending

Sprint 14.1 strengthens the delivered builder without changing its trust model.
It adds provider-neutral local/OpenAI generation, semantic job understanding,
2-4 default memory recommendations, claim planning, recruiter critique,
improved deterministic prose, grouped coverage/warnings/evidence, quality
review, and a fictional Build Week fixture. Terra is the default live writer;
Sol review is optional and off by default. Deterministic validation remains the
final gate before persistence, and the full automated suite runs without a key.
The single fictional-data live smoke is deliberately pending user confirmation.

### Sprint 14.1.2: Application Question/Answer Contract Alignment — implemented, live acceptance pending

Sprint 14.1.2 makes application questions explicit structured inputs and maps
answers one-to-one by `question_id`. Required questions receive exactly one
non-empty answer in input order; optional unanswered questions can be omitted,
and no questions means no generated snippets. Missing required answers are
structural failures eligible for one targeted answer-only repair, while valid
resume and cover-letter output is preserved. Existing evidence-backed factual
claim checks and private/demo-shared data policy remain authoritative. No live
OpenAI request was run for Sprint 14.1.2; live acceptance remains pending.

### Sprint 15: Intelligent Guided Career Interview

Ask targeted, evidence-aware questions that improve weak compiled-profile
sections. The interview should create reviewable evidence/proposals, not write
directly into canonical facts.

**Definition of done:** when a project lacks methods, results, metrics, or
outputs, CareerOS asks useful questions and routes the answers through review.

### Sprint 16: Source-Aware Document Intelligence

Improve source extraction and presentation without claiming unsupported visual
understanding. Start with better source segmentation, citation locations,
document-type handling, and explicit figure/table limitations.

**Definition of done:** a user can see which source passage supports a claim and
understand when a source needs manual clarification.

### Sprint 17: Demo Mode / Seeded Showcase Flow

Create a resettable, deterministic walkthrough featuring representative project
memories, enrichment, diagnosis, proof, and a target application package.

**Definition of done:** a collaborator can run the demo locally and understand
the product loop in under ten minutes without personal data.

### Sprint 18: Application Package Tracker

Treat the Sprint 14 package as a historical object connected to application
status, follow-ups, interviews, reflections, and outcome signals.

**Definition of done:** the user can answer what they applied to, which package
was used, which proof supported it, and what happened next.

### Sprint 19: Market, Demo, and Investor Materials

Package the product narrative, demo script, architecture diagrams, user story,
MVP status, and metrics hypotheses. Validate the problem and workflow with real
users before broadening integration scope.

**Definition of done:** an interested reviewer can understand the thesis, see a
credible demo, and identify the next validation milestone.

### Sprint 20: Browser Extension / Autofill

Only after the package workflow is reliable, add read-only job extraction and
carefully reviewed autofill. Autofill should use saved, reviewed package fields
and should never silently submit an application.

**Definition of done:** supported sites can receive user-reviewed fields from a
selected application package, with clear fallbacks and no automatic submission.

## Sequencing rules

- Build intelligence and review before convenience automation.
- Build one complete personal workflow before adding integrations.
- Treat generated documents as reviewable outputs, never as new canonical facts.
- Add an external provider only when deterministic logic is insufficient and the
  evidence boundary is preserved.
- Measure whether each sprint makes the core loop clearer, faster, or more
  trustworthy for a real user.

## MVP success signals

Early validation should focus on qualitative evidence as well as speed:

- Can Arnav complete a high-quality, reviewed application package from memory
  and a job description without starting from a blank document?
- Can a reviewer explain why a claim appears and what evidence supports it?
- Does the system clearly surface missing evidence instead of inventing it?
- Can a demo observer distinguish CareerOS from a generic text generator within
  the first few minutes?
- Does the saved package make later outcome feedback and iteration easier?

The objective is trustworthy leverage, not maximal automation.
