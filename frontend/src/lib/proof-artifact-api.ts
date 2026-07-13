export type ProofArtifactType =
  | "CASE_STUDY"
  | "GITHUB_README"
  | "PORTFOLIO_PAGE"
  | "APPLICATION_UPLOAD"
  | "OUTREACH_SUMMARY"
  | "INTERVIEW_STORY"
  | "RESUME_BULLETS";

export type ProofArtifactStatus = "DRAFT" | "REVIEWED" | "READY" | "ARCHIVED";

export type ProofTargetAudience =
  | "APPLICATION_UPLOAD"
  | "PORTFOLIO"
  | "GITHUB"
  | "OUTREACH"
  | "INTERVIEW_PREP"
  | "GENERAL";

export type ProofReadinessLabel =
  | "NEEDS_EVIDENCE"
  | "DRAFTABLE"
  | "STRONG_DRAFT"
  | "READY_TO_SHARE";

export type ProofMemoryOption = {
  id: string;
  title: string;
  memory_type: string;
  evidence_count: number;
  evidence_ids: string[];
  source_labels: string[];
  confidence: number;
};

export type ProofEvidenceReference = {
  evidence_id: string;
  source_label: string;
  excerpt?: string | null;
};

export type ProofOutcomeSignal = {
  feedback_event_id: string;
  summary: string;
  guidance: string;
  caveat: string;
};

export type ProofSupportingVariants = Record<string, unknown> & {
  resume_bullets?: string[];
  cover_letter_paragraph?: string;
  outreach_blurb?: string;
  interview_answer?: string;
  github_readme_outline?: string;
};

export type ProofArtifactVersion = {
  id: string;
  artifact_id: string;
  version_number: number;
  title: string;
  claim: string;
  content: string;
  structured_sections: Record<string, unknown>;
  evidence_ids: string[];
  evidence_references: ProofEvidenceReference[];
  outcome_signal_ids: string[];
  outcome_signals: ProofOutcomeSignal[];
  warnings: string[];
  readiness_score: number;
  readiness_label: ProofReadinessLabel;
  supporting_variants: ProofSupportingVariants;
  created_at: string;
  updated_at: string;
};

export type ProofArtifact = {
  id: string;
  title: string;
  artifact_type: ProofArtifactType;
  target_role: string;
  target_audience: ProofTargetAudience;
  source_memory_id: string;
  source_memory_title: string;
  source_diagnosis_result_id?: string | null;
  status: ProofArtifactStatus;
  latest_version: ProofArtifactVersion;
  version_count: number;
  created_at: string;
  updated_at: string;
};

export type ProofArtifactCreateInput = {
  source_memory_id: string;
  target_role: string;
  target_audience: ProofTargetAudience;
  artifact_type: ProofArtifactType;
  source_diagnosis_result_id?: string;
};

export type ProofArtifactUpdateInput = {
  title?: string;
  target_role?: string;
  target_audience?: ProofTargetAudience;
  status?: ProofArtifactStatus;
};

export type ProofArtifactVersionUpdateInput = {
  title?: string;
  claim?: string;
  content?: string;
  structured_sections?: Record<string, unknown>;
  supporting_variants?: Record<string, unknown>;
};

const apiBase =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export function listEligibleProofMemories(): Promise<ProofMemoryOption[]> {
  return request(`${apiBase}/api/proof-artifacts/eligible-memories`, {
    cache: "no-store",
  });
}

export function createProofArtifact(
  input: ProofArtifactCreateInput,
): Promise<ProofArtifact> {
  return request(`${apiBase}/api/proof-artifacts`, jsonRequest("POST", input));
}

export function listProofArtifacts(): Promise<ProofArtifact[]> {
  return request(`${apiBase}/api/proof-artifacts`, { cache: "no-store" });
}

export function getProofArtifact(artifactId: string): Promise<ProofArtifact> {
  return request(`${apiBase}/api/proof-artifacts/${artifactId}`, {
    cache: "no-store",
  });
}

export function regenerateProofArtifact(
  artifactId: string,
  input: Partial<
    Pick<ProofArtifact, "target_role" | "target_audience" | "artifact_type">
  > = {},
): Promise<ProofArtifact> {
  return request(
    `${apiBase}/api/proof-artifacts/${artifactId}/regenerate`,
    jsonRequest("POST", input),
  );
}

export function updateProofArtifact(
  artifactId: string,
  input: ProofArtifactUpdateInput,
): Promise<ProofArtifact> {
  return request(
    `${apiBase}/api/proof-artifacts/${artifactId}`,
    jsonRequest("PATCH", input),
  );
}

export function updateProofArtifactVersion(
  artifactId: string,
  versionId: string,
  input: ProofArtifactVersionUpdateInput,
): Promise<ProofArtifact> {
  return request(
    `${apiBase}/api/proof-artifacts/${artifactId}/versions/${versionId}`,
    jsonRequest("PATCH", input),
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
  if (response.ok) return (await response.json()) as T;
  const body = (await response.json().catch(() => null)) as unknown;
  const detail =
    body && typeof body === "object" && "detail" in body
      ? (body as { detail?: unknown }).detail
      : undefined;
  const message =
    typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? detail
            .map((item) =>
              item && typeof item === "object" && "msg" in item
                ? String((item as { msg?: unknown }).msg)
                : "",
            )
            .filter(Boolean)
            .join(" ")
        : `CareerOS API returned ${response.status}.`;
  throw new Error(message);
}
