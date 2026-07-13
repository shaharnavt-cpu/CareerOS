import type { Metadata } from "next";

import { ProofArtifactWorkspace } from "@/components/proof-artifacts/proof-artifact-workspace";

export const metadata: Metadata = {
  title: "Proof Artifact Builder",
};

type SearchValue = string | string[] | undefined;

export default async function ProofArtifactsPage({
  searchParams,
}: {
  searchParams: Promise<{
    source_memory_id?: SearchValue;
    source_diagnosis_result_id?: SearchValue;
    target_role?: SearchValue;
  }>;
}) {
  const query = await searchParams;
  return (
    <ProofArtifactWorkspace
      initialDiagnosisResultId={first(query.source_diagnosis_result_id)}
      initialMemoryId={first(query.source_memory_id)}
      initialTargetRole={first(query.target_role)}
    />
  );
}

function first(value: SearchValue): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}
