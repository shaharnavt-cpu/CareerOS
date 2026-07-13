import type { ProofMemoryOption } from "@/lib/proof-artifact-api";

export type EnrichmentStatus =
  | "PROPOSED"
  | "APPROVED"
  | "REJECTED"
  | "ARCHIVED";

export type EnrichmentType =
  | "PROJECT_CONTEXT"
  | "PROJECT_METHOD"
  | "PROJECT_RESULT"
  | "PROJECT_LIMITATION"
  | "PROJECT_OUTPUT"
  | "PROJECT_ROLE_RELEVANCE"
  | "PROJECT_FULL_ENRICHMENT"
  | "MEMORY_MERGE_SUGGESTION";

export type MemoryResolutionKind =
  | "CREATE_NEW"
  | "ENRICH_EXISTING"
  | "DUPLICATE_PROPOSAL"
  | "POSSIBLE_MERGE"
  | "QUIET_SUPPORTING_EVIDENCE"
  | "NEEDS_USER_CONFIRMATION";

export type IdentityResolution = {
  resolution: MemoryResolutionKind;
  confidence: number;
  matched_memory_id?: string | null;
  matched_memory_title?: string | null;
  matched_proposal_id?: string | null;
  reasons: string[];
  evidence_ids: string[];
  recommended_review_action: string;
};

export type MemoryEnrichment = {
  id: string;
  target_memory: Pick<ProofMemoryOption, "id" | "title" | "memory_type">;
  status: EnrichmentStatus;
  enrichment_type: EnrichmentType;
  structured_enrichment: Record<string, unknown>;
  evidence_ids: string[];
  source_id?: string | null;
  source_label?: string | null;
  confidence: number;
  reasoning: string;
  identity_resolution: IdentityResolution;
  warnings: string[];
  proof_artifact_readiness_impact: string;
  created_at: string;
  updated_at: string;
};

const apiBase =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export function listEnrichments(): Promise<MemoryEnrichment[]> {
  return request(`${apiBase}/api/career-memory/enrichments`, {
    cache: "no-store",
  });
}

export function createEnrichment(
  memoryId: string,
  enrichmentText: string,
): Promise<MemoryEnrichment> {
  return request(
    `${apiBase}/api/career-memory/${memoryId}/enrichments`,
    jsonRequest("POST", {
      enrichment_text: enrichmentText,
      enrichment_type: "PROJECT_FULL_ENRICHMENT",
    }),
  );
}

export function updateEnrichment(
  enrichmentId: string,
  input: {
    status?: EnrichmentStatus;
    structured_enrichment?: Record<string, unknown>;
  },
): Promise<MemoryEnrichment> {
  return request(
    `${apiBase}/api/career-memory/enrichments/${enrichmentId}`,
    jsonRequest("PATCH", input),
  );
}

export function convertProposalToEnrichment(
  memoryId: string,
  proposalId: string,
): Promise<MemoryEnrichment> {
  return request(
    `${apiBase}/api/career-memory/${memoryId}/enrichments/from-proposal/${encodeURIComponent(proposalId)}`,
    jsonRequest("POST", {}),
  );
}

function jsonRequest(method: string, input: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  };
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    let message = "CareerOS could not update project evidence.";
    try {
      const body = (await response.json()) as {
        detail?: string | { message?: string };
      };
      if (typeof body.detail === "string") message = body.detail;
      else if (body.detail?.message) message = body.detail.message;
    } catch {
      // Keep the stable user-facing fallback.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}
