# CareerOS Knowledge Acquisition Pipeline

> Version: Draft 1.0

------------------------------------------------------------------------

# Purpose

The Knowledge Acquisition Pipeline is the only pathway by which new
knowledge enters CareerOS.

CareerOS transforms raw user information into trusted professional
knowledge. Documents, conversations, and external integrations produce
**knowledge proposals** rather than directly updating the user's
profile.

Only knowledge explicitly approved by the user becomes part of the
canonical Career Memory.

------------------------------------------------------------------------

# Design Principles

-   Multiple sources contribute to one Career Memory.
-   Every fact has traceable evidence.
-   AI proposes but never silently commits.
-   Users remain the final authority.
-   Knowledge is reusable across every CareerOS feature.
-   Relationships between knowledge are as valuable as the knowledge
    itself.
-   The same knowledge may appear in multiple contexts.

------------------------------------------------------------------------

# Supported Knowledge Sources

-   Resume
-   Curriculum Vitae (CV)
-   Transcript
-   LinkedIn export
-   Guided Story conversation
-   Manual entry
-   Portfolio
-   GitHub
-   Browser Extension
-   Certificates
-   Future integrations

Each source contributes evidence rather than replacing existing
knowledge.

------------------------------------------------------------------------

# Pipeline Overview

``` text
User Source
        │
        ▼
Source Adapter
        │
        ▼
Knowledge Extraction
        │
        ▼
Knowledge Proposals
        │
        ▼
Knowledge Linking
        │
        ▼
User Review
        │
        ▼
Canonical Career Memory
```

------------------------------------------------------------------------

# Stage 1 --- Source Adapters

Every input source is converted into a common internal representation so
downstream processing is independent of the original source.

Examples:

-   Resume → Parsed document
-   Transcript → Academic record
-   Conversation → Conversation transcript
-   GitHub → Repository metadata

------------------------------------------------------------------------

# Stage 2 --- Knowledge Extraction

CareerOS identifies structured entities including Education, Programs,
Experience, Projects, Achievements, Skills, Certifications,
Publications, Organizations, Awards, Leadership, Activities, and
Contacts.

Each proposal contains:

-   Proposed values
-   Source reference
-   Confidence score
-   Extraction explanation

Nothing is stored permanently during this stage.

------------------------------------------------------------------------

# Stage 3 --- Knowledge Proposals

Extracted information becomes temporary Knowledge Proposals that remain
pending until user approval.

------------------------------------------------------------------------

# Stage 4 --- Evidence Attribution

Every proposal references the evidence that produced it.

Users should always be able to answer:

> Why does CareerOS think this?

------------------------------------------------------------------------

# Stage 5 --- Knowledge Linking

CareerOS connects related entities into a professional knowledge graph
instead of isolated records.

------------------------------------------------------------------------

# Stage 6 --- Confidence Scoring

Confidence is based on source reliability, agreement between sources,
completeness, ambiguity, and extraction certainty.

Confidence guides review but never replaces it.

------------------------------------------------------------------------

# Stage 7 --- Conflict Resolution

When sources disagree, CareerOS identifies conflicts, presents competing
evidence, asks clarifying questions, and lets the user make the final
decision.

------------------------------------------------------------------------

# Stage 8 --- User Review

Users may:

-   Approve
-   Edit
-   Reject
-   Merge duplicate entities (future)

Only approved knowledge becomes canonical.

------------------------------------------------------------------------

# Stage 9 --- Canonical Career Memory

Approved knowledge becomes the single source of truth powering every
CareerOS feature.

------------------------------------------------------------------------

# Future Expansion

New integrations should require only a new Source Adapter while reusing
the existing pipeline.

------------------------------------------------------------------------

# Guiding Principle

CareerOS does not learn from documents.

CareerOS learns from people.

Documents, conversations, and external sources are evidence that help
CareerOS understand a person's professional journey.
