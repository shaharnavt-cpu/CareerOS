import type {
  DiagnosisFocus,
  FeedbackEventStatus,
  FeedbackEventType,
} from "./diagnosis-api.ts";

export function diagnosisFocusLabel(focus: DiagnosisFocus): string {
  return {
    ANALYTICS: "Analytics",
    AI_AUTOMATION: "AI / Automation",
    RESEARCH: "Research",
    QUANT_FINANCE: "Quant / Finance",
    CAMPUS_JOB: "Campus Job",
    SCHOLARSHIP_LEADERSHIP: "Scholarship / Leadership",
    GENERAL: "General",
  }[focus];
}

export function diagnosisConfidenceLabel(confidence: number): string {
  if (confidence >= 0.8) return "High confidence";
  if (confidence >= 0.55) return "Moderate confidence";
  return "Limited confidence";
}

export function evidenceStrengthLabel(strength: string): string {
  return {
    STRONG: "Strong evidence",
    MODERATE: "Moderate evidence",
    LIMITED: "Limited evidence",
  }[strength] ?? "Evidence strength unavailable";
}

export function feedbackEventTypeLabel(type: FeedbackEventType): string {
  return {
    ARTIFACT_SUCCESS: "Artifact success",
    APPLICATION_OUTCOME: "Application outcome",
    DRAFT_FEEDBACK: "Draft feedback",
    POSITIONING_RULE: "Positioning rule",
    MEMORY_USAGE_RULE: "Memory usage rule",
    GENERAL_LEARNING: "General learning",
    UNKNOWN: "Needs classification",
  }[type];
}

export function feedbackStatusLabel(status: FeedbackEventStatus): string {
  return {
    PROPOSED: "Proposed",
    APPROVED: "Approved",
    ARCHIVED: "Archived",
  }[status];
}
