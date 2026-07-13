import type { Metadata } from "next";

import { EnrichmentWorkspace } from "@/components/enrichments/enrichment-workspace";

export const metadata: Metadata = {
  title: "Project Evidence Enrichment",
};

type SearchValue = string | string[] | undefined;

export default async function EnrichmentsPage({
  searchParams,
}: {
  searchParams: Promise<{
    memory_id?: SearchValue;
    proposal_id?: SearchValue;
  }>;
}) {
  const query = await searchParams;
  return (
    <EnrichmentWorkspace
      initialMemoryId={first(query.memory_id)}
      proposalId={first(query.proposal_id)}
    />
  );
}

function first(value: SearchValue): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}
