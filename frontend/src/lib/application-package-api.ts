export type ApplicationPackageStatus = "DRAFT" | "READY" | "ARCHIVED";

export type ApplicationPackageGenerationReason =
  | "GENERATED"
  | "REGENERATED"
  | "USER_EDIT";

export type ApplicationEvidenceSourceType =
  | "APPROVED_MEMORY"
  | "APPROVED_ENRICHMENT"
  | "STRATEGY_SIGNAL"
  | "TARGET_CONTEXT";

export type ApplicationEvidenceSupportType =
  | "DIRECT"
  | "INFERRED_FRAMING"
  | "STRATEGY_ONLY"
  | "RELEVANCE_ONLY";

export type ApplicationWarningSeverity = "INFO" | "CAUTION" | "BLOCKING";

export type ApplicationQuestion = {
  question_id: string;
  question_text: string;
  required: boolean;
  maximum_length?: number | null;
  response_type?: string | null;
  relevant_target_requirement_ids?: string[];
};

export type ApplicationEvidenceTrace = {
  trace_id: string;
  source_type: ApplicationEvidenceSourceType;
  support_type: ApplicationEvidenceSupportType;
  source_label: string;
  detail: string;
  memory_id?: string | null;
  memory_title?: string | null;
  evidence_id?: string | null;
  enrichment_id?: string | null;
  outcome_signal_id?: string | null;
  caveat?: string | null;
};

export type ApplicationPackageWarning = {
  code: string;
  message: string;
  severity: ApplicationWarningSeverity;
  requirement?: string | null;
  memory_ids: string[];
};

export type RequirementCoverageItem = {
  requirement: string;
  evidence?: string[];
  memory_ids?: string[];
};

export type ApplicationRequirementCoverage = {
  strongly_supported?: RequirementCoverageItem[];
  partially_supported?: RequirementCoverageItem[];
  unsupported?: RequirementCoverageItem[];
  not_relevant_enough?: RequirementCoverageItem[];
  /** Compatibility with early Sprint 14.1 payloads. */
  not_relevant?: RequirementCoverageItem[];
};

export type ApplicationQualityReview = {
  evidence_support?: string;
  role_relevance?: string;
  specificity?: string;
  naturalness?: string;
  concision?: string;
  recruiter_readability?: string;
  genericness?: string;
  repetition?: string;
  overclaim_risk?: string;
  primary_issue?: string;
  notes?: string[];
};

export type ApplicationProviderMetadata = {
  provider?: string;
  model?: string | null;
  review_model?: string | null;
  review_pass_ran?: boolean;
  request_id?: string | null;
  input_tokens?: number | null;
  cached_input_tokens?: number | null;
  output_tokens?: number | null;
  latency_ms?: number | null;
};

export type ApplicationEvidenceGroup = {
  memory_id?: string | null;
  memory_title?: string;
  direct_proof?: string[];
  approved_enrichment?: string[];
  supported_framing?: string[];
  strategy_signals?: string[];
  target_relevance?: string[];
};

export type ApplicationWarningGroups = {
  strongly_supported?: string[];
  partially_supported?: ApplicationPackageWarning[];
  unsupported?: ApplicationPackageWarning[];
  missing_proof?: ApplicationPackageWarning[];
};

export type ApplicationJobUnderstanding = {
  role_family: string;
  seniority: string;
  central_objective: string;
  core_responsibilities: string[];
  must_have_requirements: string[];
  preferred_requirements: string[];
  technical_expectations: string[];
  communication_expectations: string[];
  concrete_tools_requiring_direct_proof: string[];
  generic_concepts: string[];
};

export type ApplicationClaimPlan = {
  primary_positioning: string;
  primary_proof: string;
  secondary_proof: string[];
  supported_requirements: string[];
  partially_supported_requirements: string[];
  unsupported_requirements: string[];
  claims_not_to_make: string[];
  missing_evidence: string[];
  resume_strategy: string;
  cover_letter_narrative_strategy: string;
  snippet_strategy: string;
  tone: string;
};

export type ApplicationWritingIntelligence = {
  job_understanding: ApplicationJobUnderstanding;
  requirement_coverage: ApplicationRequirementCoverage;
  claim_plan: ApplicationClaimPlan;
  strategy_notes: string[];
};

export type ApplicationValidationSummary = {
  status: string;
  unsupported_claims_removed: number;
  blocking_issue_count: number;
  notes: string[];
  repairs: ApplicationValidationRepair[];
};

export type ApplicationValidationRepair = {
  code: string;
  output_section: string;
  field_path: string;
  normalized_disputed_phrase: string;
  referenced_evidence_ids: string[];
  action: string;
};

export type ResumeBullet = {
  bullet_text: string;
  evidence_trace: ApplicationEvidenceTrace[];
  confidence: number;
  warnings: string[];
  why_this_bullet: string;
};

export type ResumeBulletGroup = {
  section_suggestion: string;
  memory_id: string;
  memory_title: string;
  target_reason: string;
  bullets: ResumeBullet[];
};

export type CoverLetterParagraphTrace = {
  paragraph_label: string;
  paragraph_text: string;
  evidence_trace: ApplicationEvidenceTrace[];
};

export type CoverLetterDraft = {
  subject_or_heading: string;
  greeting: string;
  opening_paragraph: string;
  body_paragraphs: string[];
  closing_paragraph: string;
  full_text: string;
  evidence_trace_by_paragraph: CoverLetterParagraphTrace[];
  warnings: string[];
  strategy_notes: string[];
};

export type PositioningSummary = {
  primary_positioning: string;
  strongest_evidence: string;
  secondary_evidence: string[];
  risks_and_gaps: string[];
  recommended_emphasis: string[];
  do_not_claim: string[];
};

export type ApplicationSnippet = {
  question_id: string;
  question: string;
  text: string;
  evidence_trace: ApplicationEvidenceTrace[];
  warnings: string[];
};

export type SuggestedProofArtifact = {
  memory_id: string;
  memory_title: string;
  artifact_id?: string | null;
  artifact_title: string;
  action: string;
  reason: string;
};

export type ApplicationPackageOutputs = {
  positioning_summary: PositioningSummary;
  resume_bullets: ResumeBulletGroup[];
  cover_letter: CoverLetterDraft;
  application_snippets: ApplicationSnippet[];
  suggested_proof_artifacts: SuggestedProofArtifact[];
  reviewer_questions: string[];
  unsupported_claims: string[];
};

export type ApplicationClaimLedgerEntry = {
  claim_id: string;
  surface: string;
  text: string;
  memory_ids: string[];
  evidence_ids: string[];
  enrichment_ids: string[];
  proof_artifact_ids: string[];
  support_level: string;
  warnings: string[];
  user_edited: boolean;
  strategy_signal_ids: string[];
  strategy_signal_caveat?: string | null;
};

export type ApplicationPackageMemoryOption = {
  id: string;
  title: string;
  memory_type: string;
  evidence_count: number;
  source_labels: string[];
  confidence: number;
  target_reason?: string | null;
  recommended?: boolean;
  recommendation_rank?: number | null;
};

export type ApplicationPackageVersion = {
  id: string;
  package_id: string;
  version_number: number;
  target_snapshot: Record<string, unknown>;
  selected_memory_ids: string[];
  input_fingerprint: string;
  outputs: ApplicationPackageOutputs;
  evidence_trace: ApplicationEvidenceTrace[];
  warnings: ApplicationPackageWarning[];
  claim_ledger: ApplicationClaimLedgerEntry[];
  memory_ids_used: string[];
  enrichment_ids_used: string[];
  outcome_signal_ids_used: string[];
  user_edits: Record<string, unknown>;
  generator_version: string;
  generation_reason: ApplicationPackageGenerationReason;
  writing_intelligence?: ApplicationWritingIntelligence;
  requirement_coverage?: ApplicationRequirementCoverage;
  quality_review?: ApplicationQualityReview;
  provider_metadata?: ApplicationProviderMetadata;
  validation_summary?: ApplicationValidationSummary;
  created_at: string;
};

export type ApplicationPackage = {
  package_id: string;
  opportunity_id?: string | null;
  display_name: string;
  role_title: string;
  company?: string | null;
  location?: string | null;
  job_type?: string | null;
  target_description: string;
  required_skills: string[];
  preferred_skills: string[];
  responsibilities: string[];
  application_questions: ApplicationQuestion[];
  selected_memory_ids: string[];
  status: ApplicationPackageStatus;
  latest_version?: ApplicationPackageVersion | null;
  versions: ApplicationPackageVersion[];
  version_count: number;
  is_stale: boolean;
  positioning_summary?: PositioningSummary | null;
  resume_bullets: ResumeBulletGroup[];
  cover_letter?: CoverLetterDraft | null;
  application_snippets: ApplicationSnippet[];
  suggested_proof_artifacts: SuggestedProofArtifact[];
  evidence_trace: ApplicationEvidenceTrace[];
  warnings: ApplicationPackageWarning[];
  reviewer_questions: string[];
  memory_ids_used: string[];
  enrichment_ids_used: string[];
  outcome_signal_ids_used: string[];
  unsupported_claims: string[];
  writing_intelligence?: ApplicationWritingIntelligence | null;
  requirement_coverage?: ApplicationRequirementCoverage | null;
  quality_review?: ApplicationQualityReview | null;
  provider_metadata?: ApplicationProviderMetadata | null;
  validation_summary?: ApplicationValidationSummary | null;
  evidence_groups?: ApplicationEvidenceGroup[];
  warning_groups?: ApplicationWarningGroups;
  created_at: string;
  updated_at: string;
};

export type ApplicationPackageListItem = {
  package_id: string;
  display_name: string;
  role_title: string;
  company?: string | null;
  status: ApplicationPackageStatus;
  selected_memory_ids: string[];
  version_count: number;
  latest_version_number?: number | null;
  is_stale: boolean;
  created_at: string;
  updated_at: string;
};

export type ApplicationPackageCreateInput = {
  opportunity_id?: string | null;
  display_name?: string | null;
  role_title: string;
  company?: string | null;
  location?: string | null;
  job_type?: string | null;
  target_description?: string;
  required_skills?: string[];
  preferred_skills?: string[];
  responsibilities?: string[];
  application_questions?: ApplicationQuestion[];
  selected_memory_ids?: string[];
};

export type ApplicationPackageUpdateInput = Partial<
  Omit<ApplicationPackageCreateInput, "role_title">
> & {
  role_title?: string;
  status?: ApplicationPackageStatus;
};

export type ApplicationPackageGenerateInput = {
  selected_memory_ids?: string[];
  application_questions?: ApplicationQuestion[];
};

export type ApplicationPackageOutputsUpdateInput = {
  positioning_summary?: PositioningSummary;
  resume_bullets?: ResumeBulletGroup[];
  cover_letter?: CoverLetterDraft;
  application_snippets?: ApplicationSnippet[];
  suggested_proof_artifacts?: SuggestedProofArtifact[];
  reviewer_questions?: string[];
  edit_summary?: string;
};

const apiBase =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export function listEligibleApplicationPackageMemories(
  targetRole?: string,
): Promise<ApplicationPackageMemoryOption[]> {
  const query = new URLSearchParams();
  if (targetRole?.trim()) query.set("target_role", targetRole.trim());
  const suffix = query.toString();
  return request(
    `${apiBase}/api/application-packages/eligible-memories${suffix ? `?${suffix}` : ""}`,
    { cache: "no-store" },
  );
}

export function createApplicationPackage(
  input: ApplicationPackageCreateInput,
): Promise<ApplicationPackage> {
  return request(
    `${apiBase}/api/application-packages`,
    jsonRequest("POST", input),
  );
}

export function listApplicationPackages(
  includeArchived = false,
): Promise<ApplicationPackageListItem[]> {
  const suffix = includeArchived ? "?include_archived=true" : "";
  return request(`${apiBase}/api/application-packages${suffix}`, {
    cache: "no-store",
  });
}

export function getApplicationPackage(
  packageId: string,
): Promise<ApplicationPackage> {
  return request(`${apiBase}/api/application-packages/${packageId}`, {
    cache: "no-store",
  });
}

export function generateApplicationPackage(
  packageId: string,
  input: ApplicationPackageGenerateInput = {},
): Promise<ApplicationPackage> {
  return request(
    `${apiBase}/api/application-packages/${packageId}/generate`,
    jsonRequest("POST", input),
  );
}

export function regenerateApplicationPackage(
  packageId: string,
  input: ApplicationPackageGenerateInput = {},
): Promise<ApplicationPackage> {
  return request(
    `${apiBase}/api/application-packages/${packageId}/regenerate`,
    jsonRequest("POST", input),
  );
}

export function updateApplicationPackage(
  packageId: string,
  input: ApplicationPackageUpdateInput,
): Promise<ApplicationPackage> {
  return request(
    `${apiBase}/api/application-packages/${packageId}`,
    jsonRequest("PATCH", input),
  );
}

export function updateApplicationPackageOutputs(
  packageId: string,
  input: ApplicationPackageOutputsUpdateInput,
): Promise<ApplicationPackage> {
  return request(
    `${apiBase}/api/application-packages/${packageId}/outputs`,
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
        : body &&
            typeof body === "object" &&
            "error" in body &&
            typeof (body as { error?: { message?: unknown } }).error?.message ===
              "string"
          ? String((body as { error: { message: string } }).error.message)
          : undefined;
  throw new Error(message || `CareerOS API returned ${response.status}.`);
}
