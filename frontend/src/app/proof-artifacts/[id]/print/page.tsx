import type { Metadata } from "next";

import { ProofArtifactPrintView } from "@/components/proof-artifacts/proof-artifact-print-view";

export const metadata: Metadata = {
  title: "Print proof artifact",
};

export default async function ProofArtifactPrintPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ProofArtifactPrintView artifactId={id} />;
}
