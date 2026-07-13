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

export type FeedbackArtifactType =
  | "COVER_LETTER"
  | "RESUME"
  | "APPLICATION"
  | "DRAFT"
  | "PROJECT"
  | "OTHER";

export type FeedbackOutcomeType = "INTERVIEW_INVITE" | "CALLBACK" | "OFFER";

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

export type OutcomeSignal = {
  feedback_event_id: string;
  artifact_type?: FeedbackArtifactType | null;
  artifact_label?: string | null;
  outcome?: FeedbackOutcomeType | null;
  summary: string;
  guidance: string;
  caveat: string;
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
  outcome_signals: OutcomeSignal[];
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
  artifact_type?: FeedbackArtifactType | null;
  artifact_label?: string | null;
  outcome?: FeedbackOutcomeType | null;
  event_metadata: Record<string, unknown>;
  related_memory_ids: string[];
  related_opportunity_id?: string | null;
  related_draft_id?: string | null;
  suggested_future_use: string;
  status: FeedbackEventStatus;
  created_at: string;
  updated_at: string;
};

export class DiagnosisApiError extends Error {
  code?: string;
  existingEventId?: string;

  constructor(message: string, code?: string, existingEventId?: string) {
    super(message);
    this.name = "DiagnosisApiError";
    this.code = code;
    this.existingEventId = existingEventId;
  }
}

export function isDuplicateFeedbackError(
  error: unknown,
): error is DiagnosisApiError {
  return (
    error instanceof DiagnosisApiError &&
    error.code === "DUPLICATE_FEEDBACK_EVENT"
  );
}

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
      : detail &&
          typeof detail === "object" &&
          "message" in detail &&
          typeof (detail as { message?: unknown }).message === "string"
        ? (detail as { message: string }).message
      : typeof structured?.message === "string"
        ? structured.message
        : `CareerOS API returned ${response.status}.`;
  const code =
    detail &&
    typeof detail === "object" &&
    "code" in detail &&
    typeof (detail as { code?: unknown }).code === "string"
      ? (detail as { code: string }).code
      : undefined;
  const existingEventId =
    detail &&
    typeof detail === "object" &&
    "existing_event_id" in detail &&
    typeof (detail as { existing_event_id?: unknown }).existing_event_id ===
      "string"
      ? (detail as { existing_event_id: string }).existing_event_id
      : undefined;
  throw new DiagnosisApiError(message, code, existingEventId);
}
