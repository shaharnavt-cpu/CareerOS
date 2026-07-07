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
    QUEUED: "Queued",
    READING: "Reading",
    EXTRACTING_EVIDENCE: "Extracting evidence",
    COMPARING_SOURCES: "Comparing sources",
    PREPARING_PROPOSALS: "Preparing proposals",
    COMPLETE: "Complete",
    FAILED: "Needs attention",
  }[stage] ?? stage.replaceAll("_", " ").toLowerCase();
}
