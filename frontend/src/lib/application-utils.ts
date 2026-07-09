import type {
  ApplicationDraftStatus,
  ApplicationMemoryMatch,
} from "./application-api.ts";
import type { ReviewProposalType } from "./knowledge-api.ts";

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
