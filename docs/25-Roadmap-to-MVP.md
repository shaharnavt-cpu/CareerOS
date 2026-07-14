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
6. save what was used for the application and record what happened afterward.

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
| Tailored resume and cover letter | Next must-have | Sprint 14; must reuse the compiler/proof layer. |
| Save a complete application package | Next must-have | Sprint 14 should create a reviewable snapshot. |
| Guided memory-gap interview | Important next | Sprint 15 improves the quality of future proof. |
| Seeded showcase flow | Important for demos | Sprint 17 turns the product into a repeatable walkthrough. |
| Browser extension/autofill | Deferred | Valuable only after the intelligence and package workflow are dependable. |

## Remaining must-haves

These are necessary for a useful personal and demo MVP:

1. **Reviewed Resume and Cover Letter Builder.** Generate materials only from
   approved memory, approved enrichment, compiled profiles, proof artifacts,
   diagnosis, and target context. Every substantive claim must be traceable.
2. **Application package snapshot.** Preserve the target opportunity, selected
   memories, evidence/enrichment references, generated drafts, warnings, and
   user edits as a saveable historical package.
3. **Clear review/export workflow.** Make it easy to compare a draft against its
   evidence, copy it, and export a practical representation without silently
   overwriting the base resume.
4. **Guided gap collection.** Ask the smallest useful questions when evidence is
   thin instead of producing weaker prose.
5. **Demo data and guided walkthrough.** A deterministic seed path must allow a
   reviewer to see the value without setting up a personal knowledge base first.

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
- advanced model providers or agentic workflows.

## Recommended next seven sprints

### Sprint 14: Resume and Cover Letter Builder

Build a reviewed application-package workspace from approved canonical memory,
approved enrichment, compiled profiles, proof artifacts, diagnosis, and target
job text. Include evidence traces, claim warnings, copy/export-friendly output,
and an immutable package snapshot. See
[14-Resume-Cover-Letter-Builder.md](specs/14-Resume-Cover-Letter-Builder.md).

**Definition of done:** one target job produces a reviewable package containing
tailored resume bullets, cover letter, positioning summary, evidence trace,
warnings, and a saveable snapshot without invented achievements.

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
