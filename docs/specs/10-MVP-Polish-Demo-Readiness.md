# MVP Polish and Demo Readiness

## Status

Implemented and merged as Sprint 10. This is the formal architecture backfill
for the navigation, resilience, visual identity, and demonstration loop. The
existing `docs/19-MVP-Demo-Readiness.md` remains the operational runbook.

## Problem

The underlying intelligence loop can work while the product still feels
fragile: users may not know where to go next, a temporary backend failure may
look like empty data, and polished prose may hide the evidence and approval
state that make CareerOS trustworthy. A demo-ready MVP must make the whole
journey legible and recoverable.

## Goal

Provide a calm, coherent path from listening to review, approved Career Memory,
story ingredients, and application drafts. Every major surface should have
loading, empty, success, and failure behavior, with a safe next action.

## User flow

1. Start at onboarding and add a resume, transcript, or pasted source.
2. Watch Universal Listening progress through queued, active, complete, or
   failed stages; retry a retryable failure.
3. Continue to Review and decide which evidence-backed proposals become memory.
4. Land on Dashboard to see approved counts, pending review, evidence count,
   completeness, recent activity, and suggested next actions.
5. Open Stories to shape approved memories into story ingredients or proposals.
6. Open Applications to map an opportunity to approved memory and draft an
   evidence-backed response.

The dashboard is the command center for this loop. It should make “what can I
do next?” more obvious than “what did the system do internally?”

## Core concepts

- **MVP loop**: Listen → Review → Approve → Shape stories → Draft application.
- **Safe next action**: a link or retry that advances the user without
  discarding data.
- **Degraded state**: the backend or database is unavailable, but existing
  client-visible work is still described accurately.
- **Evidence-first polish**: visual refinement must increase trust and clarity,
  not hide provenance.
- **Demo reset**: an explicitly developer-only local browser reset that does
  not wipe persisted Career Memory.

## Data model / backend behavior

Sprint 10 does not introduce a new intelligence data model. It composes the
existing listening jobs, durable review proposals, canonical memory, story
records, application opportunities, matches, and drafts.

The backend must preserve stable response contracts and distinguish:

- no records from an unavailable service;
- a retryable listening failure from a terminal validation failure;
- pending review from approved canonical memory;
- a saved draft from a submitted application.

Health and persistence status are surfaced where needed so the frontend can
explain whether PostgreSQL is available, whether a listening job can be
retried, and whether Career Memory was saved.

## Frontend behavior

Navigation should expose the main surfaces as one product, with links for
onboarding/listening, review, dashboard, stories, and applications. The
dashboard provides suggested actions based on current durable counts:

- pending proposals → Review;
- approved memory → Stories and Applications;
- any saved evidence → Add another source.

Resilience requirements:

- show an explicit loading message while hydrating backend state;
- show useful empty states that name the next action;
- show actionable error messages and retry controls;
- keep the browser error boundary recoverable with reset and dashboard paths;
- preserve parsed or local work when persistence is temporarily unavailable;
- make retry behavior idempotent from the user’s perspective.

Visual identity follows the professional memory studio direction: warm neutrals,
deep green, soft borders, clear hierarchy, restrained motion, and high
contrast. Use language such as “approved memory,” “evidence trail,” “story
ingredients,” “application fit map,” and “draft from approved memory.” Avoid
generic AI-chat framing, unsupported claims, heavy animation, low-contrast
text, and game-like mechanics.

When demo tools are enabled through `NEXT_PUBLIC_DEMO_TOOLS=true` or
`NEXT_PUBLIC_DEVELOPER_TOOLS=true`, the dashboard may offer “Reset local demo
browser state.” This clears local/session convenience state only; it must say
that backend Career Memory was not changed.

## Product rules

- No polished surface may hide approval state or evidence provenance.
- Every empty or failure state must offer a safe next step.
- Never represent an API failure as an empty profile.
- Demo helpers must be explicit, gated, and non-destructive to backend data.
- The user should be able to recover from a failed request without restarting
  the entire loop.
- Visual consistency is subordinate to truthfulness and readability.
- The MVP may be narrow, but every supported path should be demonstrable end to
  end.

## Known limitations

- The browser extension and automated form filling are not part of the demo.
- Local deterministic reasoning is intentionally limited and transparent.
- Story intelligence is a foundation; it is not a finished narrative
  generator.
- The current demo environment still relies on local PostgreSQL and a stable
  demo identity.
- Resilience is primarily request-level; offline synchronization is not
  implemented.

## Future follow-ups

- Add authenticated multi-user navigation and tenant-aware health messaging.
- Add a formal design-token system and accessibility audit across all surfaces.
- Add offline-safe draft editing and queued persistence.
- Add observability for hydration failures, retries, and demo-path completion.
- Expand the demo loop into real application tracking and outcome learning.
