import type { ReviewProposalType } from "@/lib/knowledge-api";

export type ApplicationOpportunityStatus =
  | "ANALYZED"
  | "NEEDS_MEMORY"
  | "SAVED"
  | "ARCHIVED";

export type ApplicationQuestionType =
  | "WHY_THIS_ROLE"
  | "WHY_THIS_COMPANY"
  | "TELL_ME_ABOUT_YOURSELF"
  | "EXPERIENCE_EXAMPLE"
  | "LEADERSHIP"
  | "TECHNICAL_SKILLS"
  | "PROJECT_EXPLANATION"
  | "STRENGTHS"
  | "GENERAL_COVER_LETTER"
  | "UNKNOWN";

export type ApplicationDraftStatus = "DRAFT" | "EDITED" | "APPROVED" | "ARCHIVED";
export type ApplicationDraftType =
  | "GENERAL_RESPONSE"
  | "COVER_LETTER_SNIPPET"
  | "QUESTION_ANSWER";
export type ApplicationDraftLength = "SHORT" | "MEDIUM" | "DETAILED" | "LONG";

export type ApplicationMemory = {
  id: string;
  memory_type: ReviewProposalType;
  title: string;
  structured_fields: Record<string, unknown>;
  evidence_ids: string[];
  source_ids: string[];
  confidence: number;
  review_proposal_id: string;
  updated_at: string;
};

export type ApplicationQuestion = {
  id: string;
  opportunity_id: string;
  question_text: string;
  question_type: ApplicationQuestionType;
  detected_intent: string;
  required_themes: string[];
  status: "OPEN" | "DRAFTED" | "ANSWERED" | "ARCHIVED";
  created_at: string;
  updated_at: string;
};

export type ApplicationMemoryMatch = {
  id: string;
  opportunity_id: string;
  question_id?: string | null;
  canonical_memory_id: string;
  match_score: number;
  match_reason: string;
  evidence_ids: string[];
  themes_matched: string[];
  memory: ApplicationMemory;
};

export type ApplicationDraft = {
  id: string;
  opportunity_id: string;
  question_id?: string | null;
  draft_type: ApplicationDraftType;
  prompt: string;
  draft_text: string;
  evidence_ids: string[];
  status: ApplicationDraftStatus;
  draft_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ApplicationStoryContext = {
  id: string;
  title: string;
  summary: string;
  evidence_ids: string[];
  confidence: number;
};

export type ApplicationOpportunity = {
  id: string;
  title: string;
  organization?: string | null;
  raw_text: string;
  detected_role_type?: string | null;
  detected_skills: string[];
  detected_keywords: string[];
  detected_responsibilities: string[];
  detected_questions: string[];
  status: ApplicationOpportunityStatus;
  gaps: string[];
  questions: ApplicationQuestion[];
  matches: ApplicationMemoryMatch[];
  drafts: ApplicationDraft[];
  approved_stories: ApplicationStoryContext[];
  created_at: string;
  updated_at: string;
};

export type ApplicationOpportunityListItem = {
  id: string;
  title: string;
  organization?: string | null;
  detected_role_type?: string | null;
  detected_skills: string[];
  status: ApplicationOpportunityStatus;
  match_count: number;
  draft_count: number;
  created_at: string;
  updated_at: string;
};

export type ApplicationDraftResponse = {
  draft: ApplicationDraft;
  matches_used: ApplicationMemoryMatch[];
  evidence_used: string[];
};

const apiBase =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export async function createApplicationOpportunity(input: {
  raw_text: string;
  title?: string;
  organization?: string;
}): Promise<ApplicationOpportunity> {
  return request(`${apiBase}/api/applications/opportunities`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function listApplicationOpportunities(): Promise<
  ApplicationOpportunityListItem[]
> {
  return request(`${apiBase}/api/applications/opportunities`);
}

export async function getApplicationOpportunity(
  opportunityId: string,
): Promise<ApplicationOpportunity> {
  return request(`${apiBase}/api/applications/opportunities/${opportunityId}`);
}

export async function rematchApplicationOpportunity(
  opportunityId: string,
): Promise<{ opportunity: ApplicationOpportunity; matches: ApplicationMemoryMatch[]; gaps: string[] }> {
  return request(`${apiBase}/api/applications/opportunities/${opportunityId}/match`, {
    method: "POST",
  });
}

export async function draftApplicationOpportunity(
  opportunityId: string,
  input: {
    question_id?: string | null;
    draft_type?: ApplicationDraftType;
    length?: ApplicationDraftLength;
  } = {},
): Promise<ApplicationDraftResponse> {
  return request(`${apiBase}/api/applications/opportunities/${opportunityId}/draft`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function draftApplicationQuestion(
  questionId: string,
  input: {
    draft_type?: ApplicationDraftType;
    length?: ApplicationDraftLength;
  } = {},
): Promise<ApplicationDraftResponse> {
  return request(`${apiBase}/api/applications/questions/${questionId}/draft`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function updateApplicationDraft(
  draftId: string,
  input: { draft_text?: string; status?: ApplicationDraftStatus },
): Promise<ApplicationDraft> {
  return request(`${apiBase}/api/applications/drafts/${draftId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (response.ok) return (await response.json()) as T;
  const body = (await response.json().catch(() => null)) as {
    detail?: string;
    error?: { message?: string };
  } | null;
  throw new Error(
    body?.error?.message ?? body?.detail ?? `CareerOS API returned ${response.status}.`,
  );
}
