# Build Week Changes

## Before Build Week

Sprint 14 already had a trustworthy Application Package Builder: durable
packages, positioning, resume bullets, cover letters, application snippets,
proof suggestions, evidence traces, warnings, immutable versions, audited
manual edits, stale-output detection, archive/restore, `READY` gating, and a
local deterministic generator. Its main weakness was writing quality and
intelligence: default selection was too broad, requirement matching was too
literal, evidence and warnings were repetitive, and prose could sound like
compiled fields joined together.

## Added during Build Week

Sprint 14.1 adds a provider-neutral application-writing contract with local and
OpenAI implementations, a multi-stage job-understanding/ranking/claim-planning/
drafting/critic/validation pipeline, 2-4 default memory selection, semantic
requirement groups, more natural deterministic writing, grouped warnings and
evidence, quality review, safe provider metadata, and the fictional Maya Chen
demo path.

The OpenAI path uses the Responses API, strict Structured Outputs,
`store=false`, server-only credentials, configurable models and limits, typed
error handling, at most one bounded structured repair, and deterministic
post-generation validation. Terra is the cost-safe default; the optional Sol
review is disabled unless explicitly enabled. Normal tests use mocks and need
no key. Non-live verification is complete; the final one-call live smoke remains
paused until the user explicitly approves it.

## Sprint 14.1.1 hardening

Two controlled Terra outputs reached CareerOS and were rejected before
persistence: validation reported an outcome-object mismatch in one and an
unproved tool/deployment claim in the other. Withholding both drafts while
those diagnoses were unresolved was the intended trust posture; Sprint 14.1.1
hardens the contract and diagnostics rather than weakening those checks.

CareerOS now supplies immutable evidence atoms and requires exact structured
claim records for every candidate-facing positioning, resume, cover-letter, and
application-answer field. Job analysis, unsupported requirements, missing-proof
and do-not-claim warnings, target tool lists, reviewer questions, and quality/
critic/validation notes are explicitly analysis-only. A tool can appear there
as a gap, but candidate experience still requires a direct cited atom.

Outcomes are checked as structured source/action/object/result/qualifier/
certainty/metric records, allowing harmless paraphrase while blocking material
change or cross-project transfer. A narrow pre-persistence sanitizer can remove
only separable optional unsupported-warning text and records the repair; it
never rewrites a central claim. Safe diagnostics expose only an allowlisted
rule code, section/path, normalized phrase, evidence IDs, expected category,
and surface classification.

The final adversarial pass also checks clause-level factual additions, unknown
tool syntax even when tool metadata is omitted, collective-actor changes,
unstructured result wording, safe-looking prefix injection, and incidental
collaboration nouns that do not prove shared authorship.

The hardening adds no migration and leaves the Sprint 14.1 migration unchanged.
Non-live verification passed backend Ruff, all 343 backend tests, Alembic
current/check, frontend lint/typecheck, all 52 frontend tests, and the production
build. `RUN_LIVE_OPENAI_TESTS` remains `false`, and no further provider request
is part of this work without explicit user approval.

## Sprint 14.1.2 question/answer alignment

A later controlled diagnostic returned fewer application answers than the
consumer expected. This was a structural question/answer mismatch, not a
factual-claim or privacy failure. Sprint 14.1.2 removes fixed answer-count
assumptions and persists explicit ordered questions with stable `question_id`
values, `required`, optional `maximum_length`, optional `response_type`, and
`relevant_target_requirement_ids` where relevant.

Both local and OpenAI providers now return answers keyed to the supplied IDs.
Every required question needs exactly one non-empty answer in input order;
unknown or duplicate IDs fail, optional unanswered questions may be omitted,
and zero questions produces zero snippets. The Maya Chen fixture intentionally
supplies the three required `motivation`, `complex-data-project`, and
`quality-reliability` questions, but that fixture size is not a global rule.

One missing required answer may receive a targeted answer-only repair with the
missing questions, valid package sections, relevant evidence atoms, prohibited
claims, and strict answer schema. CareerOS merges only the repaired answers and
revalidates everything, preserving valid resume/cover-letter content and any
prior immutable version on failure. Repaired answers remain subject to all
Sprint 14.1.1 evidence, tool, outcome, and cross-memory checks. The data-policy
boundary is unchanged. No live request was run for Sprint 14.1.2; live OpenAI
acceptance remains pending.

Migration `20260721_0013` persists ordered application questions on package
workspaces. Final non-live verification passed backend Ruff, all 359 backend
tests, Alembic current/check at `20260721_0013 (head)`, frontend lint/typecheck,
all 52 frontend tests, and the production build (14/14 pages generated).

## Meaningful Codex use

Codex accelerated the work as an engineering collaborator across the existing
modular monolith: it audited a tightly coupled generation service and trust
boundaries, designed a provider seam that preserves versioning and validation,
implemented backend/frontend changes and regression coverage, produced a safe
fictional demo fixture and gated smoke path, updated operating documentation,
and ran the non-live verification loop. It extended the existing architecture
instead of replacing the proven Sprint 14 workflow.

## Meaningful GPT-5.6 use

GPT-5.6 is not a decorative chat call. Terra is responsible for semantic job
understanding, evidence prioritization, claim planning, role-aware application
writing, and a concise recruiter self-review inside one strict structured
response. CareerOS then independently checks immutable evidence-atom references,
claim-surface classification, structured outcomes, concrete tools, and factual
claims before saving. When explicitly enabled, Sol reviews and rewrites the
complete structured package for recruiter readability without adding claims or
evidence. This division uses GPT-5.6 for the parts where language intelligence
matters while CareerOS remains authoritative for truth and trust.

## Preserved guarantees

Existing package IDs, manual selection/order, copy/edit behavior, immutable
versions, audited edits, stale-output protections, `READY`, and archive/restore
remain part of the contract. Provider failure does not erase a valid package or
create an empty version. Explicit question IDs and optional/zero-question
behavior apply to both providers. Local deterministic generation remains a
complete offline fallback.
