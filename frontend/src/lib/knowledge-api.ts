import type { KnowledgeCategory } from "@/lib/onboarding-data";

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
  | "CERTIFICATE";

export type EvidenceReference = {
  source_id: string;
  source_type: SourceType;
  title: string;
  excerpt: string;
  location?: string | null;
  verification_status: string;
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

export async function generateKnowledgeProposals(input: {
  raw_source: string;
  source_type: SourceType;
  source_name: string;
}): Promise<ReasoningResponse> {
  const response = await fetch(`${apiBase}/api/knowledge/proposals`, {
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
  const response = await fetch(`${apiBase}/api/knowledge/proposals/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ proposal, decision }),
  });
  return parseResponse(response);
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.ok) return (await response.json()) as T;
  const body = (await response.json().catch(() => null)) as {
    detail?: string;
  } | null;
  throw new Error(body?.detail ?? `CareerOS API returned ${response.status}.`);
}

export function mergeProposals(
  current: KnowledgeProposal[],
  incoming: KnowledgeProposal[],
): KnowledgeProposal[] {
  const merged = new Map(current.map((proposal) => [proposal.id, proposal]));
  incoming.forEach((proposal) => merged.set(proposal.id, proposal));
  return [...merged.values()];
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

export function saveUploadedSource(source: string) {
  window.sessionStorage.setItem(sourceStorageKey, source);
}

export function takeUploadedSource(): string | null {
  const source = window.sessionStorage.getItem(sourceStorageKey);
  window.sessionStorage.removeItem(sourceStorageKey);
  return source;
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
