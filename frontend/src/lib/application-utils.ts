import type {
  ApplicationDraft,
  ApplicationDraftLength,
  ApplicationDraftStatus,
  ApplicationMemoryMatch,
} from "./application-api.ts";
import type { ReviewProposalType } from "./knowledge-api.ts";

export type DraftMemoryMetadata = {
  id: string;
  title: string;
  type: ReviewProposalType;
  evidence_count: number;
  themes_matched: string[];
};

export function applicationMemoryTypeLabel(type: ReviewProposalType): string {
  return type
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function evidenceCountLabel(count: number): string {
  return `${count} evidence reference${count === 1 ? "" : "s"}`;
}

export function applicationMatchSummary(
  matches: Pick<ApplicationMemoryMatch, "id">[],
  gaps: string[],
): string {
  if (!matches.length) {
    return "No approved memories matched yet. Approve relevant Career Memory first.";
  }
  const memoryText = `${matches.length} relevant memor${matches.length === 1 ? "y" : "ies"}`;
  if (!gaps.length) return `CareerOS found ${memoryText} from approved memory.`;
  return `CareerOS found ${memoryText}; ${gaps.length} gap${gaps.length === 1 ? "" : "s"} still need evidence.`;
}

export function draftStatusLabel(status: ApplicationDraftStatus): string {
  return {
    DRAFT: "Draft",
    EDITED: "Edited",
    APPROVED: "Approved",
    ARCHIVED: "Archived",
  }[status];
}

export function draftVariantLabel(length: ApplicationDraftLength): string {
  return {
    SHORT: "Short",
    MEDIUM: "Medium",
    DETAILED: "Detailed",
    LONG: "Detailed",
  }[length];
}

export function draftUsesApprovedMemoryOnly(draft: ApplicationDraft): boolean {
  return draft.draft_metadata.uses_approved_memory_only === true;
}

export function draftPrimaryMemory(
  draft: ApplicationDraft,
): DraftMemoryMetadata | null {
  return memoryMetadata(draft.draft_metadata.primary_memory);
}

export function draftSupportingMemories(
  draft: ApplicationDraft,
): DraftMemoryMetadata[] {
  const raw = draft.draft_metadata.supporting_memories;
  if (!Array.isArray(raw)) return [];
  return raw.flatMap((item) => {
    const memory = memoryMetadata(item);
    return memory ? [memory] : [];
  });
}

function memoryMetadata(value: unknown): DraftMemoryMetadata | null {
  if (!value || typeof value !== "object") return null;
  const data = value as Record<string, unknown>;
  if (typeof data.id !== "string" || typeof data.title !== "string") {
    return null;
  }
  return {
    id: data.id,
    title: data.title,
    type:
      typeof data.type === "string"
        ? (data.type as ReviewProposalType)
        : "NEEDS_CLASSIFICATION",
    evidence_count:
      typeof data.evidence_count === "number" ? data.evidence_count : 0,
    themes_matched: Array.isArray(data.themes_matched)
      ? data.themes_matched.map(String)
      : [],
  };
}
