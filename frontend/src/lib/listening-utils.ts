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
