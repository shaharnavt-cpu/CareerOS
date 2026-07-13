export type DiagnosisFocus =
  | "ANALYTICS"
  | "AI_AUTOMATION"
  | "RESEARCH"
  | "QUANT_FINANCE"
  | "CAMPUS_JOB"
  | "SCHOLARSHIP_LEADERSHIP"
  | "GENERAL";

export type DiagnosisSessionStatus =
  | "RUNNING"
  | "COMPLETE"
  | "NEEDS_MEMORY"
  | "FAILED";

export type FeedbackEventType =
  | "ARTIFACT_SUCCESS"
  | "APPLICATION_OUTCOME"
  | "DRAFT_FEEDBACK"
  | "POSITIONING_RULE"
  | "MEMORY_USAGE_RULE"
  | "GENERAL_LEARNING"
  | "UNKNOWN";

export type FeedbackEventStatus = "PROPOSED" | "APPROVED" | "ARCHIVED";

export type DiagnosisEvidenceItem = {
  memory_id: string;
  memory_title: string;
  memory_type: string;
  relevant_themes: string[];
  claim_supported: string;
  evidence_ids: string[];
  strength: string;
  confidence: number;
  reason_code: string;
};

export type ProofSprint = {
  objective: string;
  actions: string[];
  expected_artifact: string;
  why_it_matters: string;
  evidence_to_strengthen: string[];
  application_use: string;
};

export type DiagnosisResult = {
  id: string;
  session_id: string;
  career_identity: string;
  identity_rationale: string;
  evidence_map: DiagnosisEvidenceItem[];
  recognition_gap: string;
  missing_proof: string[];
  proof_sprint: ProofSprint;
  do_not_waste_time: string;
  exact_next_actions: string[];
  exact_messages: Record<string, string>;
  confidence: number;
  evidence_ids: string[];
  feedback_event_ids: string[];
  diagnosis_version: string;
  created_at: string;
  updated_at: string;
};

export type DiagnosisSession = {
  id: string;
  target_role?: string | null;
  target_context?: string | null;
  frustration_context?: string | null;
  selected_focus?: DiagnosisFocus | null;
  status: DiagnosisSessionStatus;
  approved_memory_only: boolean;
  result: DiagnosisResult;
  created_at: string;
  updated_at: string;
};

export type CareerFeedbackEvent = {
  id: string;
  raw_note: string;
  event_type: FeedbackEventType;
  structured_summary: string;
  related_memory_ids: string[];
  related_opportunity_id?: string | null;
  related_draft_id?: string | null;
  suggested_future_use: string;
  status: FeedbackEventStatus;
  created_at: string;
  updated_at: string;
};

const apiBase =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export async function createDiagnosisSession(input: {
  target_role?: string;
  target_context?: string;
  frustration_context?: string;
  selected_focus?: DiagnosisFocus;
}): Promise<DiagnosisSession> {
  return request(`${apiBase}/api/diagnosis/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function listDiagnosisSessions(): Promise<DiagnosisSession[]> {
  return request(`${apiBase}/api/diagnosis/sessions`, { cache: "no-store" });
}

export async function rerunDiagnosisSession(
  diagnosisSessionId: string,
): Promise<DiagnosisSession> {
  return request(
    `${apiBase}/api/diagnosis/sessions/${diagnosisSessionId}/rerun`,
    { method: "POST" },
  );
}

export async function createFeedbackEvent(input: {
  raw_note: string;
  status?: FeedbackEventStatus;
}): Promise<CareerFeedbackEvent> {
  return request(`${apiBase}/api/diagnosis/feedback-events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function listFeedbackEvents(): Promise<CareerFeedbackEvent[]> {
  return request(`${apiBase}/api/diagnosis/feedback-events`, {
    cache: "no-store",
  });
}

export async function updateFeedbackEvent(
  feedbackEventId: string,
  input: { status?: FeedbackEventStatus; raw_note?: string },
): Promise<CareerFeedbackEvent> {
  return request(`${apiBase}/api/diagnosis/feedback-events/${feedbackEventId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (response.ok) return (await response.json()) as T;
  const body = (await response.json().catch(() => null)) as unknown;
  const detail =
    body && typeof body === "object" && "detail" in body
      ? (body as { detail?: unknown }).detail
      : undefined;
  const structured =
    body && typeof body === "object" && "error" in body
      ? (body as { error?: { message?: unknown } }).error
      : undefined;
  const message =
    typeof detail === "string"
      ? detail
      : typeof structured?.message === "string"
        ? structured.message
        : `CareerOS API returned ${response.status}.`;
  throw new Error(message);
}
