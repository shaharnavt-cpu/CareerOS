import type { KnowledgeCategory } from "@/lib/onboarding-data";
import { mergeById, replacePendingById } from "@/lib/listening-utils";

export type EntityType =
  | "EDUCATION"
  | "PROGRAM"
  | "EXPERIENCE"
  | "PROJECT"
  | "ACHIEVEMENT"
  | "SKILL";

export type ApprovalState =
  | "DISCOVERED"
  | "NEEDS_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "CANONICAL";

export type SourceType =
  | "RESUME"
  | "CONVERSATION"
  | "MANUAL"
  | "TRANSCRIPT"
  | "LINKEDIN"
  | "PORTFOLIO"
  | "GITHUB"
  | "CERTIFICATE"
  | "GENERIC_DOCUMENT";

export type EvidenceReference = {
  source_id: string;
  source_type: SourceType;
  title: string;
  excerpt: string;
  location?: string | null;
  verification_status: string;
  evidence_id?: string | null;
  category?: string | null;
  confidence?: number | null;
  corroborated: boolean;
};

export type Clarification = {
  question: string;
  reason:
    | "MISSING_EVIDENCE"
    | "CONFLICTING_EVIDENCE"
    | "LOW_CONFIDENCE";
  detail: string;
};

export type KnowledgeProposal = {
  id: string;
  entity_type: EntityType;
  proposed_value: Record<string, unknown>;
  operation: "CREATE" | "UPDATE" | "LINK";
  confidence: number;
  evidence: EvidenceReference[];
  reasoning_summary: string;
  clarification?: Clarification | null;
  approval_state: ApprovalState;
  duplicate_of?: string | null;
  relationships: {
    target_proposal_id: string;
    relationship_type: string;
  }[];
};

export type ReasoningResponse = {
  source_id: string;
  proposals: KnowledgeProposal[];
  summary: {
    normalized_lines: number;
    extracted_candidates: number;
    proposals: number;
    provider: string;
  };
};

const apiBase =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";
const proposalStorageKey = "careeros.knowledge-proposals";
const sourceStorageKey = "careeros.uploaded-source";
const listeningSourceIdsKey = "careeros.listening-source-ids";

export type PendingSource = {
  raw_text: string;
  source_type: SourceType;
  label: string;
  original_filename?: string;
  media_type?: string;
};

export type ListeningSource = {
  id: string;
  source_type: SourceType;
  label: string;
  original_filename?: string | null;
  status: "RECEIVED" | "LISTENING" | "READY" | "FAILED";
  evidence_count: number;
};

export type PipelineStage =
  | "UPLOAD"
  | "DETECT_DOCUMENT_TYPE"
  | "PARSE_DOCUMENT"
  | "EXTRACT_TEXT"
  | "CREATE_EVIDENCE"
  | "PERSIST_EVIDENCE"
  | "COMPARE_KNOWLEDGE"
  | "GENERATE_PROPOSALS"
  | "COMPLETE";

export type StageTiming = {
  stage: PipelineStage;
  status: "PENDING" | "ACTIVE" | "COMPLETE" | "FAILED";
  started_at?: string | null;
  completed_at?: string | null;
  duration_ms?: number | null;
  message: string;
};

export type ListeningFailure = {
  code: string;
  friendly_message: string;
  stage: PipelineStage;
  retryable: boolean;
  occurred_at: string;
  developer_message?: string | null;
  exception_type?: string | null;
  stack_trace?: string | null;
};

export type ListeningJob = {
  id: string;
  filename: string;
  media_type?: string | null;
  status: "QUEUED" | "ACTIVE" | "COMPLETE" | "FAILED";
  current_stage: PipelineStage;
  message: string;
  attempt: number;
  retry_count: number;
  elapsed_ms: number;
  source_id?: string | null;
  source_type?: SourceType | null;
  document_type?: string | null;
  detection_confidence?: number | null;
  extracted_character_count: number;
  evidence_count: number;
  persistence_status: "NOT_STARTED" | "SAVING" | "SAVED" | "FAILED";
  failure?: ListeningFailure | null;
  proposals: KnowledgeProposal[];
  stages: StageTiming[];
  diagnostics?: {
    extracted_character_count: number;
    evidence_count: number;
    persistence_status: string;
    stage_timings: StageTiming[];
    developer_logs: Record<string, unknown>[];
    database_error?: string | null;
  } | null;
  created_at: string;
  updated_at: string;
};

export type HealthResponse = {
  status: "ok" | "degraded";
  api: "available";
  database: {
    status: "unknown" | "available" | "unavailable";
    checked_at?: string | null;
    latency_ms?: number | null;
    error_code?: string | null;
    message?: string | null;
    developer_message?: string | null;
    exception_type?: string | null;
    stack_trace?: string | null;
  };
};

export type ApiDiagnostic = {
  timestamp: string;
  method: string;
  url: string;
  status?: number;
  duration_ms: number;
  response?: unknown;
  error?: string;
};

const apiDiagnostics: ApiDiagnostic[] = [];

export class CareerOSApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly developerDetail?: unknown,
  ) {
    super(message);
    this.name = "CareerOSApiError";
  }
}

export function getApiDiagnostics(): ApiDiagnostic[] {
  return [...apiDiagnostics];
}

function recordApiDiagnostic(diagnostic: ApiDiagnostic) {
  apiDiagnostics.unshift(diagnostic);
  apiDiagnostics.splice(50);
}

async function apiFetch(url: string, init?: RequestInit): Promise<Response> {
  const started = performance.now();
  const method = init?.method ?? "GET";
  try {
    const response = await fetch(url, init);
    const responseBody = await response
      .clone()
      .json()
      .catch(() => null);
    recordApiDiagnostic({
      timestamp: new Date().toISOString(),
      method,
      url,
      status: response.status,
      duration_ms: Math.round((performance.now() - started) * 100) / 100,
      response: responseBody,
    });
    return response;
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    recordApiDiagnostic({
      timestamp: new Date().toISOString(),
      method,
      url,
      duration_ms: Math.round((performance.now() - started) * 100) / 100,
      error: detail,
    });
    throw new CareerOSApiError(
      "API_UNAVAILABLE",
      "CareerOS cannot reach the listening service. Check that the backend is running, then retry.",
      detail,
    );
  }
}

export async function uploadListeningFiles(
  files: File[],
): Promise<{ jobs: ListeningJob[] }> {
  const body = new FormData();
  files.forEach((file) => body.append("files", file, file.name));
  const response = await apiFetch(`${apiBase}/api/listening/uploads`, {
    method: "POST",
    body,
  });
  return parseResponse(response);
}

export async function listListeningJobs(
  developer = false,
): Promise<ListeningJob[]> {
  const response = await apiFetch(
    `${apiBase}/api/listening/jobs${developer ? "?developer=true" : ""}`,
    {
    cache: "no-store",
    },
  );
  return parseResponse(response);
}

export async function retryListeningJob(jobId: string): Promise<ListeningJob> {
  const response = await apiFetch(
    `${apiBase}/api/listening/jobs/${jobId}/retry`,
    { method: "POST" },
  );
  return parseResponse(response);
}

export async function getHealth(
  developer = false,
  refresh = false,
): Promise<HealthResponse> {
  const query = new URLSearchParams();
  if (developer) query.set("developer", "true");
  if (refresh) query.set("refresh", "true");
  const response = await apiFetch(
    `${apiBase}/api/health${query.size ? `?${query}` : ""}`,
    { cache: "no-store" },
  );
  return parseResponse(response);
}

export async function submitListeningSource(
  input: PendingSource,
): Promise<{ source: ListeningSource }> {
  const response = await apiFetch(`${apiBase}/api/listening/sources`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse(response);
}

export async function generateListeningProposals(
  sourceIds: string[],
): Promise<{
  proposals: KnowledgeProposal[];
  clusters_considered: number;
  evidence_considered: number;
  provider: string;
}> {
  const response = await apiFetch(`${apiBase}/api/listening/proposals`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_ids: sourceIds }),
  });
  return parseResponse(response);
}

export async function generateKnowledgeProposals(input: {
  raw_source: string;
  source_type: SourceType;
  source_name: string;
}): Promise<ReasoningResponse> {
  const response = await apiFetch(`${apiBase}/api/knowledge/proposals`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<ReasoningResponse>(response);
}

export async function reviewKnowledgeProposal(
  proposal: KnowledgeProposal,
  decision: "APPROVE" | "REJECT",
): Promise<{ proposal: KnowledgeProposal; canonical_entity_id?: string | null }> {
  const response = await apiFetch(`${apiBase}/api/knowledge/proposals/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ proposal, decision }),
  });
  return parseResponse(response);
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.ok) return (await response.json()) as T;
  const body = (await response.json().catch(() => null)) as {
    detail?: string | { code?: string; message?: string };
    error?: { code?: string; message?: string };
  } | null;
  const structured = body?.error ??
    (typeof body?.detail === "object" ? body.detail : undefined);
  const message =
    structured?.message ??
    (typeof body?.detail === "string" ? body.detail : undefined) ??
    `CareerOS API returned ${response.status}.`;
  throw new CareerOSApiError(
    structured?.code ?? `HTTP_${response.status}`,
    message,
    body,
  );
}

export function mergeProposals(
  current: KnowledgeProposal[],
  incoming: KnowledgeProposal[],
): KnowledgeProposal[] {
  return mergeById(current, incoming);
}

export function replacePendingProposals(
  current: KnowledgeProposal[],
  incoming: KnowledgeProposal[],
): KnowledgeProposal[] {
  return replacePendingById(current, incoming);
}

export function rememberListeningSource(sourceId: string): string[] {
  const ids = loadListeningSourceIds();
  const next = [...new Set([...ids, sourceId])];
  window.sessionStorage.setItem(listeningSourceIdsKey, JSON.stringify(next));
  return next;
}

function loadListeningSourceIds(): string[] {
  if (typeof window === "undefined") return [];
  const value = window.sessionStorage.getItem(listeningSourceIdsKey);
  if (!value) return [];
  try {
    const parsed = JSON.parse(value) as unknown;
    return Array.isArray(parsed)
      ? parsed.filter((item): item is string => typeof item === "string")
      : [];
  } catch {
    return [];
  }
}

export function saveProposals(proposals: KnowledgeProposal[]) {
  if (typeof window !== "undefined") {
    window.sessionStorage.setItem(proposalStorageKey, JSON.stringify(proposals));
  }
}

export function loadProposals(): KnowledgeProposal[] {
  if (typeof window === "undefined") return [];
  const value = window.sessionStorage.getItem(proposalStorageKey);
  if (!value) return [];
  try {
    return JSON.parse(value) as KnowledgeProposal[];
  } catch {
    return [];
  }
}

export function saveUploadedSource(source: PendingSource) {
  window.sessionStorage.setItem(sourceStorageKey, JSON.stringify(source));
}

export function takeUploadedSource(): PendingSource | null {
  const source = window.sessionStorage.getItem(sourceStorageKey);
  window.sessionStorage.removeItem(sourceStorageKey);
  if (!source) return null;
  try {
    const parsed = JSON.parse(source) as PendingSource;
    if (parsed.raw_text && parsed.source_type && parsed.label) return parsed;
  } catch {
    return {
      raw_text: source,
      source_type: "RESUME",
      label: "Uploaded resume",
    };
  }
  return null;
}

const categories: Record<EntityType, KnowledgeCategory> = {
  EDUCATION: "Education",
  PROGRAM: "Programs",
  EXPERIENCE: "Experience",
  PROJECT: "Projects",
  ACHIEVEMENT: "Achievements",
  SKILL: "Skills",
};

export function proposalCategory(proposal: KnowledgeProposal) {
  return categories[proposal.entity_type];
}

export function proposalTitle(proposal: KnowledgeProposal): string {
  for (const key of ["name", "title", "institution_name", "organization_name"]) {
    const value = proposal.proposed_value[key];
    if (typeof value === "string" && value) return value;
  }
  return proposal.entity_type.toLowerCase();
}

export function proposalDetail(proposal: KnowledgeProposal): string {
  const ignored = new Set([
    "name",
    "title",
    "institution_name",
    "normalized_name",
  ]);
  const details = Object.entries(proposal.proposed_value)
    .filter(([key, value]) => !ignored.has(key) && value != null && value !== "")
    .slice(0, 3)
    .map(([, value]) =>
      Array.isArray(value) ? value.join(", ") : String(value),
    );
  return details.join(" · ") || proposal.reasoning_summary;
}

export function proposalPrimaryField(proposal: KnowledgeProposal): string {
  if (proposal.entity_type === "EDUCATION") return "institution_name";
  if (proposal.entity_type === "PROGRAM" || proposal.entity_type === "SKILL") {
    return "name";
  }
  return "title";
}

export function clarificationReasonLabel(reason: Clarification["reason"]) {
  return {
    MISSING_EVIDENCE: "Missing evidence",
    CONFLICTING_EVIDENCE: "Conflicting evidence",
    LOW_CONFIDENCE: "Low confidence",
  }[reason];
}
