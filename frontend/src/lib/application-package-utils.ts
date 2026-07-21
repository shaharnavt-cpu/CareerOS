import type {
  ApplicationEvidenceSourceType,
  ApplicationEvidenceSupportType,
  ApplicationPackageGenerationReason,
  ApplicationPackageMemoryOption,
  ApplicationProviderMetadata,
  ApplicationQuestion,
  ApplicationPackageOutputs,
  ApplicationPackageStatus,
  ApplicationPackageVersion,
  ApplicationWarningSeverity,
  ResumeBulletGroup,
} from "./application-package-api";

export type ApplicationPackageInput = {
  opportunityId?: string | null;
  roleTitle: string;
  company?: string | null;
  location?: string | null;
  jobType?: string | null;
  targetDescription: string;
  requiredSkills: string[];
  preferredSkills: string[];
  responsibilities: string[];
  applicationQuestions: ApplicationQuestion[];
  selectedMemoryIds: string[];
};

export type NormalizedApplicationPackageInput = {
  opportunity_id: string | null;
  role_title: string;
  company: string | null;
  location: string | null;
  job_type: string | null;
  target_description: string;
  required_skills: string[];
  preferred_skills: string[];
  responsibilities: string[];
  application_questions: ApplicationQuestion[];
  selected_memory_ids: string[];
};

const statusLabels: Record<ApplicationPackageStatus, string> = {
  DRAFT: "Draft",
  READY: "Ready",
  ARCHIVED: "Archived",
};

const sourceLabels: Record<ApplicationEvidenceSourceType, string> = {
  APPROVED_MEMORY: "Approved memory",
  APPROVED_ENRICHMENT: "Approved enrichment",
  STRATEGY_SIGNAL: "Strategy signal · not proof",
  TARGET_CONTEXT: "Target context · relevance only",
};

const supportLabels: Record<ApplicationEvidenceSupportType, string> = {
  DIRECT: "Direct support",
  INFERRED_FRAMING: "Supported framing",
  STRATEGY_ONLY: "Strategy only · not factual proof",
  RELEVANCE_ONLY: "Relevance only · not factual proof",
};

const severityLabels: Record<ApplicationWarningSeverity, string> = {
  INFO: "Review note",
  CAUTION: "Caution",
  BLOCKING: "Needs resolution",
};

const generationLabels: Record<ApplicationPackageGenerationReason, string> = {
  GENERATED: "Generated",
  REGENERATED: "Regenerated",
  USER_EDIT: "Saved edits",
};

export function splitPackageList(value: string): string[] {
  return normalizeList(value.split(/[\n,;]+/));
}

export function normalizeApplicationPackageInput(
  input: ApplicationPackageInput,
): NormalizedApplicationPackageInput {
  return {
    opportunity_id: nullableText(input.opportunityId),
    role_title: input.roleTitle.trim(),
    company: nullableText(input.company),
    location: nullableText(input.location),
    job_type: nullableText(input.jobType),
    target_description: input.targetDescription.trim(),
    required_skills: normalizeList(input.requiredSkills),
    preferred_skills: normalizeList(input.preferredSkills),
    responsibilities: normalizeList(input.responsibilities),
    application_questions: input.applicationQuestions.map((question) => ({
      question_id: question.question_id.trim(),
      question_text: question.question_text.trim(),
      required: question.required,
      maximum_length: question.maximum_length ?? null,
      response_type: nullableText(question.response_type),
      relevant_target_requirement_ids: normalizeIdentifiers(
        question.relevant_target_requirement_ids ?? [],
      ),
    })),
    selected_memory_ids: input.selectedMemoryIds.map((id) => id.trim()),
  };
}

export function applicationPackageInputFingerprint(
  input: ApplicationPackageInput,
): string {
  return JSON.stringify(normalizeApplicationPackageInput(input));
}

export function packageMatchesInput(
  applicationPackage: {
    is_stale: boolean;
    latest_version?: Pick<
      ApplicationPackageVersion,
      "target_snapshot" | "selected_memory_ids"
    > | null;
  },
  input: ApplicationPackageInput,
): boolean {
  const version = applicationPackage.latest_version;
  if (!version || applicationPackage.is_stale) return false;
  return (
    applicationPackageInputFingerprint(applicationPackageVersionInput(version)) ===
    applicationPackageInputFingerprint(input)
  );
}

export function applicationPackageVersionInput(
  version: Pick<
    ApplicationPackageVersion,
    "target_snapshot" | "selected_memory_ids"
  >,
): ApplicationPackageInput {
  const target = version.target_snapshot;
  return {
    opportunityId: stringOrNull(target.opportunity_id),
    roleTitle: stringValue(target.role_title),
    company: stringOrNull(target.company),
    location: stringOrNull(target.location),
    jobType: stringOrNull(target.job_type),
    targetDescription: stringValue(target.target_description),
    requiredSkills: stringList(target.required_skills),
    preferredSkills: stringList(target.preferred_skills),
    responsibilities: stringList(target.responsibilities),
    applicationQuestions: applicationQuestionList(target.application_questions),
    selectedMemoryIds: [...version.selected_memory_ids],
  };
}

export function moveSelectedMemory(
  ids: string[],
  memoryId: string,
  direction: -1 | 1,
): string[] {
  const currentIndex = ids.indexOf(memoryId);
  const nextIndex = currentIndex + direction;
  if (
    currentIndex < 0 ||
    nextIndex < 0 ||
    nextIndex >= ids.length
  ) {
    return [...ids];
  }
  const next = [...ids];
  [next[currentIndex], next[nextIndex]] = [next[nextIndex], next[currentIndex]];
  return next;
}

export function defaultRecommendedMemoryIds(
  memories: ApplicationPackageMemoryOption[],
  maximum = 4,
): string[] {
  const recommended = memories
    .filter((memory) => memory.recommended === true)
    .sort(
      (left, right) =>
        (left.recommendation_rank ?? Number.MAX_SAFE_INTEGER) -
          (right.recommendation_rank ?? Number.MAX_SAFE_INTEGER) ||
        left.title.localeCompare(right.title),
    )
    .slice(0, maximum);
  return recommended.length >= 2
    ? recommended.map((memory) => memory.id)
    : [];
}

export function applicationProviderLabel(
  metadata: ApplicationProviderMetadata | null | undefined,
): string {
  const modelLabel = (model: string | null | undefined): string => {
    if (model === "gpt-5.6-terra") return "GPT-5.6 Terra";
    if (model === "gpt-5.6-sol") return "GPT-5.6 Sol";
    return model ?? "OpenAI";
  };
  if (!metadata?.provider) return "Generation details unavailable";
  if (metadata.provider === "local-deterministic") return "Local deterministic";
  if (metadata.provider === "openai") {
    if (metadata.review_pass_ran && metadata.review_model) {
      return `${modelLabel(metadata.model)} + ${modelLabel(metadata.review_model)} review`;
    }
    if (metadata.model === "gpt-5.6-terra") return modelLabel(metadata.model);
    return metadata.model ? `OpenAI · ${metadata.model}` : "OpenAI";
  }
  return metadata.model
    ? `${metadata.provider} · ${metadata.model}`
    : metadata.provider.replaceAll("-", " ");
}

export function resumeApplicationClaimId(
  groupIndex: number,
  bulletIndex: number,
): string {
  return `resume-${groupIndex + 1}-${bulletIndex + 1}`;
}

export function snippetApplicationClaimId(index: number): string {
  return `snippet-${index + 1}`;
}

export function applicationPackageStatusLabel(
  status: ApplicationPackageStatus,
): string {
  return statusLabels[status];
}

export function applicationEvidenceSourceLabel(
  source: ApplicationEvidenceSourceType,
): string {
  return sourceLabels[source];
}

export function applicationEvidenceSupportLabel(
  support: ApplicationEvidenceSupportType,
): string {
  return supportLabels[support];
}

export function applicationWarningSeverityLabel(
  severity: ApplicationWarningSeverity,
): string {
  return severityLabels[severity];
}

export function applicationGenerationReasonLabel(
  reason: ApplicationPackageGenerationReason,
): string {
  return generationLabels[reason];
}

export function resumeBulletGroupText(group: ResumeBulletGroup): string {
  return group.bullets.map((bullet) => `• ${bullet.bullet_text.trim()}`).join("\n");
}

export function applicationPackageCopyText(
  outputs: ApplicationPackageOutputs,
): string {
  const bullets = outputs.resume_bullets
    .map(
      (group) =>
        `${group.section_suggestion} — ${group.memory_title}\n${resumeBulletGroupText(group)}`,
    )
    .join("\n\n");
  const snippets = outputs.application_snippets
    .map((snippet) => `${snippet.question}\n${snippet.text}`)
    .join("\n\n");
  return [
    "POSITIONING SUMMARY",
    outputs.positioning_summary.primary_positioning,
    "",
    "RESUME BULLETS",
    bullets,
    "",
    "COVER LETTER",
    outputs.cover_letter.full_text,
    "",
    "APPLICATION ANSWERS",
    snippets,
  ]
    .join("\n")
    .trim();
}

function normalizeList(values: string[]): string[] {
  const result: string[] = [];
  const seen = new Set<string>();
  for (const value of values) {
    const cleaned = value.replace(/\s+/g, " ").trim();
    const key = cleaned.toLocaleLowerCase();
    if (!cleaned || seen.has(key)) continue;
    seen.add(key);
    result.push(cleaned);
  }
  return result;
}

function normalizeIdentifiers(values: string[]): string[] {
  const result: string[] = [];
  const seen = new Set<string>();
  for (const value of values) {
    const cleaned = value.trim();
    if (!cleaned || seen.has(cleaned)) continue;
    seen.add(cleaned);
    result.push(cleaned);
  }
  return result;
}

function nullableText(value: string | null | undefined): string | null {
  const rendered = value?.trim() ?? "";
  return rendered || null;
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function stringOrNull(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String) : [];
}

function applicationQuestionList(value: unknown): ApplicationQuestion[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const question = item as Record<string, unknown>;
    const maximumLength = question.maximum_length;
    return [{
      question_id: stringValue(question.question_id),
      question_text: stringValue(question.question_text),
      required:
        typeof question.required === "boolean" ? question.required : true,
      maximum_length:
        typeof maximumLength === "number" && Number.isFinite(maximumLength)
          ? maximumLength
          : null,
      response_type: stringOrNull(question.response_type),
      relevant_target_requirement_ids: stringList(
        question.relevant_target_requirement_ids,
      ),
    }];
  });
}
