import type {
  ProofArtifactStatus,
  ProofArtifactType,
  ProofArtifactVersion,
  ProofReadinessLabel,
  ProofTargetAudience,
} from "./proof-artifact-api";

const typeLabels: Record<ProofArtifactType, string> = {
  CASE_STUDY: "Case study",
  GITHUB_README: "GitHub README",
  PORTFOLIO_PAGE: "Portfolio page",
  APPLICATION_UPLOAD: "Application upload",
  OUTREACH_SUMMARY: "Outreach summary",
  INTERVIEW_STORY: "Interview story",
  RESUME_BULLETS: "Resume bullets",
};

const audienceLabels: Record<ProofTargetAudience, string> = {
  APPLICATION_UPLOAD: "Optional application upload",
  PORTFOLIO: "Portfolio",
  GITHUB: "GitHub",
  OUTREACH: "Outreach",
  INTERVIEW_PREP: "Interview prep",
  GENERAL: "General",
};

const readinessLabels: Record<ProofReadinessLabel, string> = {
  NEEDS_EVIDENCE: "Needs evidence",
  DRAFTABLE: "Draftable",
  STRONG_DRAFT: "Strong draft",
  READY_TO_SHARE: "Ready to share",
};

const statusLabels: Record<ProofArtifactStatus, string> = {
  DRAFT: "Draft",
  REVIEWED: "Reviewed",
  READY: "Ready",
  ARCHIVED: "Archived",
};

export function proofArtifactTypeLabel(value: ProofArtifactType): string {
  return typeLabels[value];
}

export function proofAudienceLabel(value: ProofTargetAudience): string {
  return audienceLabels[value];
}

export function proofReadinessLabel(value: ProofReadinessLabel): string {
  return readinessLabels[value];
}

export function proofArtifactStatusLabel(value: ProofArtifactStatus): string {
  return statusLabels[value];
}

export function buildProofArtifactHref(input: {
  sourceMemoryId?: string | null;
  sourceDiagnosisResultId?: string | null;
  targetRole?: string | null;
}): string {
  const query = new URLSearchParams();
  if (input.sourceMemoryId) query.set("source_memory_id", input.sourceMemoryId);
  if (input.sourceDiagnosisResultId) {
    query.set("source_diagnosis_result_id", input.sourceDiagnosisResultId);
  }
  if (input.targetRole) query.set("target_role", input.targetRole);
  const suffix = query.toString();
  return `/proof-artifacts${suffix ? `?${suffix}` : ""}`;
}

export function proofVariantText(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    return value.map((item) => `- ${String(item)}`).join("\n");
  }
  return "";
}

export function proofCaseStudyText(version: ProofArtifactVersion): string {
  return version.content.trim();
}
