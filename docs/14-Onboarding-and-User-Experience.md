# CareerOS Onboarding & User Experience

> Version: Draft 1.0  
> Status: Product Specification  
> Last Updated: July 2026

---

## 1. Purpose

This document defines the onboarding and first-use experience for CareerOS.

It is the authoritative specification for Sprint 3: Conversational Onboarding.

CareerOS should not begin by asking users to manually fill out a database. It should learn from the user's existing documents, natural language explanations, and follow-up clarifications, then organize that information into structured career knowledge for user approval.

---

## 2. Core Product Principle

CareerOS should understand the user before asking the user to understand CareerOS.

The user should not need to know whether something is an education record, experience, achievement, project, program, or evidence item before entering it.

CareerOS should allow the user to describe their story naturally, then extract structured knowledge from it.

---

## 3. Onboarding Philosophy

Traditional career tools use a form-first workflow:

```text
User fills fields
↓
Tool stores fields
↓
Tool generates documents
```

CareerOS uses a conversation-first workflow:

```text
User uploads documents and tells their story
↓
CareerOS extracts facts, relationships, and uncertainty
↓
User reviews and corrects extracted knowledge
↓
CareerOS saves approved knowledge
```

Forms are still useful, but primarily as editing tools after CareerOS has already created a structured draft.

---

## 4. First Launch Experience

The first screen should combine document upload and conversation.

The user should see:

```text
Welcome to CareerOS

Let's build your career profile together.

Upload anything you already have, or just start by telling me your story.
CareerOS will organize everything into structured knowledge for you to review.

[ Drag and drop files here ]

Supported:
- Resume
- CV
- Transcript
- LinkedIn PDF
- Portfolio
- Research papers
- Cover letters
- Existing applications
- Certificates

[ Start with documents ]
[ Start with conversation ]
[ Skip onboarding for now ]
```

The user should never feel blocked if they do not have documents ready.

---

## 5. Supported Input Sources

CareerOS should eventually support the following onboarding inputs:

### MVP Inputs

- Resume PDF or DOCX
- CV PDF or DOCX
- Plain text pasted by the user
- Conversational chat responses

### Near-Future Inputs

- Transcript PDF
- LinkedIn profile PDF
- GitHub profile URL
- Portfolio website URL
- Research paper or poster
- Existing cover letters
- Application question answers

### Future Inputs

- Gmail/Outlook recruiting emails
- Calendar interviews
- Job tracker exports
- GitHub repositories
- Google Drive or OneDrive folders
- Handshake or LinkedIn exports

---

## 6. Upload Pipeline

When a user uploads files, CareerOS should:

1. Store the file metadata.
2. Extract text when possible.
3. Identify document type.
4. Extract candidate facts.
5. Detect uncertainty.
6. Link facts to source evidence.
7. Present extracted knowledge for review.

CareerOS should not immediately save extracted facts as trusted canonical knowledge.

All extracted information starts as proposed knowledge.

---

## 7. Conversational Career Interview

The Career Interview is the main onboarding experience.

It should feel like a guided conversation with a thoughtful career mentor.

### Goals

The Career Interview should discover:

- education history
- work experience
- research experience
- leadership experience
- volunteer work
- projects
- programs
- achievements
- skills
- evidence
- career goals
- job preferences
- application history

### Conversation Style

CareerOS should ask open-ended questions first, then focused follow-ups.

Example:

```text
CareerOS:
Tell me about your college journey. You can describe it naturally.

User:
I started at UT Austin in astronomy, joined GEVIP, worked on galaxy evolution research, completed my capstone, and presented at AAS.

CareerOS:
I found several connected items:
- UT Austin
- Astronomy degree
- GEVIP program
- Galaxy evolution research
- Capstone project
- AAS presentation

Was GEVIP a course, a research program, an organization, or something else?
```

---

## 8. Programs as First-Class Entities

Some career experiences do not fit cleanly into education, work, project, or achievement.

Examples:

- Galaxy Evolution Vertically Integrated Program
- Nash Leaders Program
- Honors programs
- Research cohorts
- Fellowship programs
- Incubators
- Selective leadership programs
- NSF REU
- NASA L'SPACE
- Startup accelerators

CareerOS should support a first-class concept called `Program`.

A Program may connect to:

- education
- experience
- project
- achievement
- skill
- mentor/contact
- evidence
- application materials

Example:

```text
UT Austin
↓
GEVIP
↓
Capstone Research
↓
AAS Poster
↓
Skills: Python, research, data analysis, scientific communication
```

This prevents duplication and allows the same real-world activity to appear in different generated views.

---

## 9. Knowledge Graph Mental Model

CareerOS should not treat resume sections as isolated containers.

Traditional sections are views over a connected knowledge graph.

### Stored Knowledge

```text
Person
Education
Program
Experience
Project
Achievement
Skill
Evidence
Contact
Application
Artifact
```

### Generated Views

```text
Resume
Cover Letter
Research CV
Scholarship Application
Interview Prep
Networking Message
LinkedIn Summary
```

The same underlying knowledge can appear differently depending on context.

---

## 10. Proposed Knowledge States

Extracted knowledge should move through states.

```text
DISCOVERED
↓
NEEDS_REVIEW
↓
APPROVED
↓
CANONICAL
```

### DISCOVERED

CareerOS found a possible fact from upload or conversation.

### NEEDS_REVIEW

CareerOS is not confident enough to save it.

### APPROVED

The user confirmed it.

### CANONICAL

The fact becomes part of the user's structured profile.

---

## 11. Confidence Levels

Every extracted item should have a confidence level.

Examples:

```text
UT Austin degree
Confidence: High
Evidence: Resume + transcript

GEVIP classification
Confidence: Medium
Evidence: Resume mention
Needs clarification: Was it a program, course, or research group?

Leadership skill
Confidence: Low
Evidence: Conversation mention only
Needs clarification: What did the user actually do?
```

Confidence should guide follow-up questions.

CareerOS should ask about low-confidence or high-importance items first.

---

## 12. Approval Workflow

After initial extraction, CareerOS should present a review screen.

Example:

```text
Here's what I understood.

Education
✓ UT Austin — B.S. Astronomy/Astrophysics
✓ UT Dallas — M.S. Business Analytics & AI

Programs
? GEVIP — Needs classification
? Nash Leaders Program — Needs dates

Projects
✓ Gas Kinematics Capstone
✓ Toyota Financial Services Hackathon

Skills
✓ Python
✓ SQL
? Machine Learning — needs evidence

Achievements
✓ AAS Poster
✓ Dean's Excellence Scholarship
```

User actions:

- Approve
- Edit
- Merge
- Delete
- Mark as unsure
- Add missing detail

Nothing becomes trusted canonical knowledge until approved.

---

## 13. Gap Detection

CareerOS should identify missing information.

Examples:

- "You mentioned a project but not what tools you used."
- "This experience has no dates."
- "This skill has no supporting evidence."
- "This achievement has a metric but no source."
- "This program is linked to a project but not to an institution."

Gap detection should be helpful, not judgmental.

---

## 14. Follow-Up Question Strategy

CareerOS should ask targeted questions.

Poor question:

```text
List all your experiences.
```

Better question:

```text
You mentioned GEVIP. Was your role closer to research assistant, student participant, or program member?
```

Poor question:

```text
What skills do you have?
```

Better question:

```text
In your capstone project, did you write Python code yourself, analyze data, present results, or all three?
```

---

## 15. User Control

The user must remain in control.

CareerOS may suggest structure, but the user decides what is true.

Important actions require approval:

- saving extracted facts
- merging duplicate entries
- classifying ambiguous experiences
- deleting proposed knowledge
- using facts in generated documents
- marking evidence as verified

---

## 16. Editing Experience

Forms should exist, but they should be used after extraction.

Editing pages should allow users to correct:

- dates
- titles
- descriptions
- relationships
- evidence links
- skill links
- confidence labels
- visibility in generated documents

The UI should make it easy to see why CareerOS believes a fact is true.

Example:

```text
Skill: Python

Supported by:
- Capstone Research
- GEVIP
- HackUTD Project
- Applied Machine Learning Labs

Confidence: High
```

---

## 17. Profile Completeness

CareerOS should show profile completeness without making users feel punished.

Example:

```text
Career Profile

Education: Strong
Projects: Strong
Skills: Good
Evidence Coverage: Needs work
Leadership: Needs clarification
Applications: Not started
```

Completeness should produce helpful suggestions:

```text
You have strong research experience, but your leadership examples are thin.
Want to spend two minutes adding leadership details?
```

---

## 18. Empty States

Empty states should guide the user.

Example for Projects:

```text
No projects yet.

You can:
- upload a resume
- describe a project in conversation
- add one manually
```

Example for Evidence:

```text
No evidence linked yet.

Evidence can include GitHub links, papers, screenshots, certificates, presentations, or transcripts.
```

---

## 19. Suggested First-Time Flow

### Step 1: Welcome

User sees upload + chat.

### Step 2: Upload

User uploads resume or skips.

### Step 3: Initial extraction

CareerOS extracts candidate knowledge.

### Step 4: Career interview

CareerOS asks broad then targeted questions.

### Step 5: Review

CareerOS shows proposed knowledge grouped by domain.

### Step 6: Approval

User approves, edits, or rejects extracted facts.

### Step 7: Profile dashboard

User lands on a dashboard showing:

- profile summary
- knowledge categories
- gaps
- next recommended action

---

## 20. MVP Sprint 3 Scope

Sprint 3 should implement the UX shell and workflow structure, not full AI extraction.

### Required

- onboarding landing screen
- upload area UI
- conversation panel UI
- mock extraction results
- review/approval UI
- profile dashboard shell
- clear separation between proposed and approved knowledge

### Not Required Yet

- real LLM extraction
- real resume parsing
- file storage
- authentication
- production AI pipeline
- document generation
- browser extension integration

Sprint 3 may use mock data as long as the flow is realistic.

---

## 21. Sprint 3 Acceptance Criteria

Sprint 3 is complete when:

- user can open onboarding page
- user can see upload options
- user can type into a conversation panel
- system can display mock extracted knowledge
- user can approve/reject/edit mock items
- user can proceed to a profile dashboard
- UI reflects conversation-first onboarding philosophy
- no unrelated product features are implemented

---

## 22. Future Sprint Scope

### Sprint 4: Real Career Knowledge API Integration

Connect approved onboarding items to backend models.

### Sprint 5: File Upload and Parsing

Support resume upload and text extraction.

### Sprint 6: AI Extraction

Use LLMs to extract structured proposed knowledge from text.

### Sprint 7: Evidence Linking

Automatically connect facts to documents and source excerpts.

### Sprint 8: Resume Generation

Generate evidence-backed resume drafts from approved knowledge.

---

## 23. AI Behavior Rules During Onboarding

CareerOS should:

- ask clarification instead of assuming
- distinguish facts from guesses
- cite source documents when possible
- avoid exaggerating achievements
- avoid inventing dates, metrics, titles, or responsibilities
- present uncertainty visibly
- ask permission before saving anything
- use plain language
- avoid overwhelming the user with too many questions at once

CareerOS should not:

- fabricate experience
- silently save inferred facts
- pressure users into completing everything
- treat uploaded documents as perfectly accurate
- overwrite approved facts without confirmation

---

## 24. Example Interaction

```text
CareerOS:
Welcome. Upload anything you already have, or tell me your story.

User:
I uploaded my resume. Also, GEVIP is hard to explain. It was a selective research program I took as a class each semester, and it connected to my capstone.

CareerOS:
Got it. I think GEVIP should be stored as a Program, linked to UT Austin, your research experience, and your capstone project.

I found these possible items:
- Program: GEVIP
- Education link: UT Austin
- Research experience: Galaxy evolution research
- Project: Gas kinematics capstone
- Achievement: AAS poster presentation

Does that structure look right?
```

---

## 25. Wireframe: First Screen

```text
+------------------------------------------------------+
| CareerOS                                             |
+------------------------------------------------------+
|                                                      |
|  Let's build your career profile together.           |
|                                                      |
|  Upload documents or just start talking.             |
|                                                      |
|  +---------------- Upload ----------------+          |
|  | Drag resume, CV, transcript, etc. here |          |
|  +----------------------------------------+          |
|                                                      |
|  Career Interview                                   |
|  +----------------------------------------+          |
|  | Tell me about your education or work...|          |
|  +----------------------------------------+          |
|                                                      |
|  [Continue] [Skip for now]                           |
|                                                      |
+------------------------------------------------------+
```

---

## 26. Wireframe: Review Screen

```text
+------------------------------------------------------+
| Here's what I understood                             |
+------------------------------------------------------+
| Education                                            |
| [✓] UT Austin — B.S. Astronomy                       |
| [✓] UT Dallas — M.S. Business Analytics & AI         |
|                                                      |
| Programs                                             |
| [?] GEVIP — needs classification                     |
|                                                      |
| Projects                                             |
| [✓] Gas Kinematics Capstone                          |
| [✓] Toyota Financial Services Hackathon              |
|                                                      |
| Skills                                               |
| [✓] Python                                           |
| [?] Machine Learning — needs evidence                |
|                                                      |
| [Approve selected] [Edit] [Ask follow-up]            |
+------------------------------------------------------+
```

---

## 27. Relationship to Database Schema

The onboarding flow should eventually create or update:

- users
- user_preferences
- education
- experiences
- projects
- achievements
- skills
- skill_links
- evidence_items
- evidence_links

Future versions may also create:

- programs
- artifacts
- ai_runs
- ai_citations
- timeline_events

The Program entity should be added in a future schema revision before real GEVIP-style modeling is implemented.

---

## 28. Required ADRs

This document implies the following product decisions:

1. Conversation-first onboarding.
2. Upload + chat as the first screen.
3. Forms as editors, not primary data entry.
4. Programs as first-class entities.
5. Career knowledge as a connected graph, not isolated categories.
6. User approval required before extracted knowledge becomes canonical.

These should be recorded in ADR-001 or separate ADRs.

---

## 29. Guiding Principle

CareerOS should not ask users to translate their life into database rows.

CareerOS should listen to their story, organize it intelligently, ask thoughtful follow-up questions, and let the user approve the truth.
