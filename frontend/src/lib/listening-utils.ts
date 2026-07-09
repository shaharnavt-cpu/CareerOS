export function mergeById<T extends { id: string }>(
  current: T[],
  incoming: T[],
): T[] {
  const merged = new Map(current.map((item) => [item.id, item]));
  incoming.forEach((item) => merged.set(item.id, item));
  return [...merged.values()];
}

export function nextListeningStep(current: number, total: number): number {
  return Math.min(current + 1, Math.max(total - 1, 0));
}

export function replacePendingById<
  T extends { id: string; approval_state: string },
>(current: T[], incoming: T[]): T[] {
  return mergeById(
    current.filter((item) => item.approval_state !== "NEEDS_REVIEW"),
    incoming,
  );
}

export function evidenceCategoryLabel(evidence: {
  category?: string | null;
  source_type: string;
}): string {
  return (evidence.category ?? evidence.source_type).replaceAll("_", " ");
}

const supportedAttachmentExtensions = new Set([
  "pdf",
  "docx",
  "txt",
  "md",
  "markdown",
  "csv",
]);

export function validateListeningAttachments(files: File[]): string | null {
  if (!files.length) return "Choose at least one document.";
  if (files.length > 10) return "Attach up to 10 files at a time.";
  const unsupported = files.find((file) => {
    const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
    return !supportedAttachmentExtensions.has(extension);
  });
  if (unsupported) {
    return `${unsupported.name} isn’t supported yet. Attach PDF, DOCX, TXT, Markdown, or CSV.`;
  }
  const oversized = files.find((file) => file.size > 15 * 1024 * 1024);
  if (oversized) return `${oversized.name} is larger than 15 MB.`;
  return null;
}

export function listeningStageLabel(stage: string): string {
  return {
    UPLOAD: "Uploaded",
    DETECT_DOCUMENT_TYPE: "Document type detected",
    PARSE_DOCUMENT: "Document parsed",
    EXTRACT_TEXT: "Text extracted",
    CREATE_EVIDENCE: "Evidence created",
    PERSIST_EVIDENCE: "Saving to Career Memory",
    COMPARE_KNOWLEDGE: "Comparing with existing knowledge",
    GENERATE_PROPOSALS: "Generating proposals",
    COMPLETE: "Complete",
  }[stage] ?? stage.replaceAll("_", " ").toLowerCase();
}

export function friendlyFailureMessage(code: string): string {
  return {
    DATABASE_UNAVAILABLE:
      "Career Memory is temporarily unavailable. Your parsed document is safe—retry when PostgreSQL is ready.",
    DATABASE_TIMEOUT:
      "Career Memory took too long to respond. Your parsed document is safe—retry when PostgreSQL is ready.",
    DATABASE_CONSTRAINT_FAILURE:
      "CareerOS found conflicting stored evidence. Your parsed document is safe and can be retried.",
    PERSISTENCE_FAILURE:
      "CareerOS couldn’t save this evidence. Your parsed document is safe and can be retried.",
    PARSER_FAILED:
      "CareerOS couldn’t parse this file. Export a fresh copy and try again.",
    EMPTY_DOCUMENT: "This document is empty. Add content or choose another file.",
    NO_TEXT_FOUND:
      "No readable text was found. This may be a scanned document that needs OCR.",
    PROPOSAL_FAILURE:
      "Your evidence is saved, but proposals could not be prepared yet. Retry when ready.",
    REASONING_FAILURE:
      "Your evidence is saved, but reasoning is temporarily unavailable. Retry when ready.",
    API_UNAVAILABLE:
      "CareerOS can’t reach the listening service. Check that the backend is running.",
  }[code] ?? "CareerOS stopped at this stage. Completed work is still available.";
}

export function reviewSummaryFromJobs(
  jobs: Array<{
    source_id?: string | null;
    evidence_count: number;
    hidden_supporting_evidence_count?: number;
    proposals: Array<{ id: string }>;
  }>,
) {
  const bySource = new Map<string, (typeof jobs)[number]>();
  jobs.forEach((job, index) => {
    bySource.set(job.source_id ?? `job-${index}`, job);
  });
  const proposals = new Set(jobs.flatMap((job) => job.proposals.map((item) => item.id)));
  return {
    proposal_count: proposals.size,
    evidence_count: [...bySource.values()].reduce(
      (total, job) => total + job.evidence_count,
      0,
    ),
    hidden_supporting_evidence_count: Math.max(
      0,
      ...jobs.map((job) => job.hidden_supporting_evidence_count ?? 0),
    ),
  };
}

type ClarifiableProposal = {
  entity_type: string;
  proposed_value: Record<string, unknown>;
  clarification?: unknown;
  review_status?: string;
  clarification_resolved_at?: string | null;
};

export function resolveProposalClarification<T extends ClarifiableProposal>(
  proposal: T,
  answer: string,
): { proposal: T; acknowledgement: string } {
  const value = answer.trim();
  const updated = { ...proposal.proposed_value };
  const department = value.match(/department of [^,.]+/i)?.[0];
  const organization = value.match(
    /organization is (?:the )?(.+?)(?:,\s*(?:specifically|under)|\s+under|\.|$)/i,
  )?.[1];

  if (proposal.entity_type === "EXPERIENCE") {
    if (organization) {
      updated.organization_name = organization.trim();
      updated.organization = organization.trim();
    } else if (updated.organization_name === "Needs clarification") {
      updated.organization_name = value.replace(/[.]$/, "");
    }
    if (department) updated.department = department;
  }

  const organizationName = String(
    updated.organization_name ?? updated.organization ?? "the updated organization",
  );
  const acknowledgement = department
    ? `Got it — I’ll record that as ${organizationName}, ${department}.`
    : `Got it — I’ll update this memory with ${value.replace(/[.]$/, "")}.`;

  return {
    proposal: {
      ...proposal,
      proposed_value: updated,
      clarification: undefined,
      review_status: "NEEDS_REVIEW",
      clarification_resolved_at: new Date().toISOString(),
    },
    acknowledgement,
  };
}
