# Project Evidence Enrichment

## What project enrichment solves

Listening can find multiple descriptions of the same project across a resume,
capstone report, poster, or pasted note. Those descriptions should deepen one
approved Career Memory instead of producing a new project card every time.

Project Evidence Enrichment adds a reviewed layer between listening evidence and
canonical memory. It answers two questions before creating another memory:

1. Is this evidence about an approved memory that already exists?
2. Should CareerOS enrich that memory, flag a possible merge, keep quiet support,
   or create something new?

The first supported workflow is `/enrichments`. A user selects an approved
project, pastes deeper project detail, reviews the extracted fields, and approves,
edits, rejects, or archives the enrichment.

## How this differs from normal listening

Listening preserves observations and synthesizes review proposals. Enrichment is
targeted: it attaches additional source-backed detail to one approved canonical
memory. It does not replace the original proposal, erase the resume-level
projection, or bypass review.

Uploaded project evidence also passes through identity resolution when review
proposals are persisted. A high-confidence project match becomes a proposed
enrichment instead of another durable project proposal. Exact pending proposal
duplicates are not recreated. Medium-confidence matches remain reviewable and
show a possible-duplicate explanation.

## Identity resolution

`MemoryIdentityResolver` is deterministic and provider-independent. It compares:

- normalized and significant project-title words;
- stable project phrases such as `Gas Kinematics` or `3D Galaxy Morphology`;
- evidence and structured-field theme overlap;
- date overlap;
- institution or organization overlap;
- existing pending proposal titles;
- explicit user selection in the targeted enrichment flow.

The resolver returns one of:

- `CREATE_NEW`;
- `ENRICH_EXISTING`;
- `DUPLICATE_PROPOSAL`;
- `POSSIBLE_MERGE`;
- `QUIET_SUPPORTING_EVIDENCE`;
- `NEEDS_USER_CONFIRMATION`.

Every result includes confidence, matched memory/proposal references when
available, user-visible reasons, evidence IDs, and a recommended review action.
Matching is deliberately conservative. The UNICORN Project remains distinct from
Gas Kinematics unless the user supplies explicit evidence that connects them.
CareerOS never merges canonical memories automatically.

## Enrichment extraction

The local deterministic extractor supports labeled or prose evidence for:

- project title and goal;
- research question;
- data or inputs;
- tools and methods;
- analysis steps;
- findings or results;
- limitations;
- outputs;
- collaborators or context;
- role relevance;
- skills demonstrated;
- resume-bullet claims;
- cover-letter angles;
- proof-artifact angles;
- warnings not to claim.

Vocabulary such as spectral data, imaging data, Gaussian fitting, statistical
analysis, modeling, uncertainty/error propagation, visualization, and technical
communication is recorded only when present in pasted or uploaded evidence.
Inconclusive results such as “no clear trend” are retained rather than upgraded
into a positive finding.

When a source contains too little project-specific text, CareerOS warns:

> CareerOS found limited project-specific text in this source. Paste the abstract,
> methods, or results section to enrich this memory.

This is the v0 response to figure-heavy or poorly parsed sources. CareerOS does
not pretend it understood charts, figures, or tables that were not extracted as
text.

## Review and persistence

`career_memory_enrichments` stores:

- the user and target canonical memory;
- optional listening source and source label;
- `PROPOSED`, `APPROVED`, `REJECTED`, or `ARCHIVED` status;
- enrichment type and structured enrichment JSON;
- evidence IDs;
- confidence and concise identity reasoning;
- identity-resolution metadata;
- parse and claim warnings;
- timestamps.

Only an approved project canonical memory can receive enrichment. A new
enrichment starts as `PROPOSED`. Approval rebuilds the enrichment projection on
the canonical memory; rejection does not change it. Archiving a previously
approved enrichment rebuilds the projection without that record.

The canonical JSON payload preserves its original fields and adds aggregated
approved fields such as:

- `enriched_context`;
- `enriched_problem`;
- `enriched_data_or_inputs`;
- `enriched_method`;
- `enriched_findings`;
- `enriched_limitations`;
- `enriched_outputs`;
- `enriched_role_relevance`;
- `enriched_role_specific_framing`;
- `enriched_skills`;
- `enriched_resume_bullets`;
- `enriched_cover_letter_angles`;
- `enriched_proof_artifact_angles`;
- `enriched_proof_artifact_summary`.

Original evidence and source IDs are retained. Approved enrichment evidence and
source IDs are added without duplication. The enrichment record remains the
review history, so removing it from the active projection does not destroy its
provenance.

## Duplicate cleanup

Review cards with a medium-confidence project match say that the proposal may be
an enrichment of an existing memory. The user can reject it normally or choose
**Convert to enrichment**. Conversion preserves the proposal evidence in a new
proposed enrichment and rejects the duplicate project proposal.

For high-confidence matches generated by listening, the duplicate project
proposal is not persisted. The proposed enrichment appears in `/enrichments` for
review.

## Downstream use

Proof Artifact Builder reads only the canonical projection, so approved
enrichment can strengthen Problem, Data or Inputs, Method, Outcome or Insight,
Limitations, What This Proves, and all channel variants. Rejected or archived
enrichment is absent from that projection and cannot guide generation.

Career Diagnosis also reads the approved projection. When a project has approved
enrichment, Recognition Gap guidance can explain that its method, data, and
limitations are now documented. Enrichment remains factual evidence; diagnosis
remains a derived judgment.

## Resume and cover-letter future hooks

Sprint 13 does not implement a Resume Builder or Cover Letter Builder. It exposes
approved future-ready fields instead:

- `resume_bullet_claims` / `enriched_resume_bullets`;
- `cover_letter_angles` / `enriched_cover_letter_angles`;
- `role_relevance`;
- `role_specific_framing` / `enriched_role_specific_framing`;
- `proof_artifact_angles`;
- `proof_artifact_summary` / `enriched_proof_artifact_summary`;
- `warnings_not_to_claim`.

A later builder can reuse those fields while still checking the underlying
evidence IDs and approved-memory boundary. They are hooks, not permission to
invent impact, tools, metrics, or outcomes.

## API

- `GET /api/memory-identity/candidates`
- `GET /api/career-memory/enrichments`
- `POST /api/career-memory/{memory_id}/enrichments`
- `GET /api/career-memory/{memory_id}/enrichments`
- `POST /api/career-memory/{memory_id}/enrichments/from-proposal/{proposal_id}`
- `PATCH /api/career-memory/enrichments/{enrichment_id}`

All resources are scoped to the current user boundary. Missing resources return
`404`; attempts to enrich an unapproved memory return `422`.

## Known limitations

- Identity resolution is deterministic vocabulary/title matching rather than
  semantic embeddings.
- Targeted v0 enrichment supports pasted text; saved uploaded evidence is
  supported by the API, while a richer source picker is future work.
- OCR, figure interpretation, table reconstruction, and slide understanding are
  not implemented.
- Extraction understands common labeled sections and bounded project vocabulary,
  not every academic or technical document structure.
- Canonical memory versioning and multi-memory merge approval remain future work.
