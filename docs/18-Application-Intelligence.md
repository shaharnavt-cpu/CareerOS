# Application Intelligence

Sprint 9 adds the application intelligence brain for CareerOS. It does not fill
forms or control a browser yet; it analyzes an opportunity, matches it to
approved Career Memory, and drafts evidence-backed responses the user can edit.

## Opportunity understanding

An application opportunity starts as pasted text: a job description, internship
posting, or application question. CareerOS stores the raw text and extracts a
structured read of the opportunity:

- likely role title and organization when present;
- role type such as internship, analytics, data, research, AI, finance, or
  student work;
- required and preferred skills such as Python, SQL, Excel, reporting, or
  dashboarding;
- responsibilities and themes such as communication, business insights,
  technical rigor, leadership, and data cleaning;
- application questions and their likely intent.

The deterministic local implementation uses transparent rules and keyword
matching so local development does not require an LLM key.

## Approved memory matching

Application Intelligence only treats `canonical_memory_records` as approved
Career Memory. Those records are created after the user approves a review
proposal. Rejected and pending review proposals are not used as application
evidence.

Each opportunity or question is matched against approved memory by comparing:

- memory type, such as project, experience, skill set, education, program, or
  achievement;
- memory title and structured fields;
- approved skill lists;
- organizations, responsibilities, summaries, and project descriptions;
- evidence IDs and confidence.

Matches are saved as `application_memory_matches` with a score, reason,
themes matched, and evidence IDs. This makes the application workspace
traceable instead of a one-off generated response.

## Evidence-backed drafts

Drafts are generated from the ranked approved-memory matches. The local
deterministic generator uses templates that cite approved memory titles and
preserve evidence IDs in draft metadata. Drafts are editable and can be saved
or approved without changing the underlying Career Memory.

CareerOS should not hallucinate unapproved facts. If a posting asks for a skill
that is not present in approved memory, the workspace shows it as a gap instead
of inventing experience.

## Draft quality rules

Sprint 9.5 improves the deterministic draft generator so drafts read like
application answers, not internal planning notes. A generated answer should:

- answer the prompt directly in first person;
- avoid repeating the question back to the user;
- avoid phrases such as "I would highlight" or "CareerOS found";
- choose one primary approved memory and up to two supporting memories;
- prefer projects or experiences for project/experience questions;
- use skill sets as support unless the prompt specifically asks about skills;
- keep evidence IDs and memory selection metadata outside the answer text.

Draft metadata records the primary memory, supporting memories, evidence count,
approved-memory-only indicator, and gaps. The user can inspect that evidence in
the workspace without forcing the answer itself to sound like a debug summary.

Supported deterministic variants are:

- Short: a compact answer for small form fields.
- Medium: a fuller answer with context and role fit.
- Detailed: a longer answer with setup, actions, supporting evidence, and
  reflection.

## Browser extension is out of scope

This sprint intentionally does not build the browser extension. Sprint 9 builds
the intelligence layer:

1. understand the opportunity;
2. match it to approved memory;
3. expose gaps;
4. draft evidence-backed responses.

That prepares Sprint 10 or a later browser-extension sprint to become the
"hands" that can fill forms using already-reviewed, evidence-backed application
drafts.
