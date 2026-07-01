# CareerOS AI Architecture

> Version: Draft 0.1

## AI Pipeline

User → Knowledge Store → Evidence Retrieval → Prompt Builder → LLM
Provider → Response Validator → Human Review → Persist Results

## Principles

-   Never invent experience.
-   Every generated claim must reference evidence.
-   Keep providers interchangeable.
-   Log prompt versions.
-   Require human approval before important actions.
