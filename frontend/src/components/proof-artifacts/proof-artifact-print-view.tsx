"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ProofArtifactDocument } from "@/components/proof-artifacts/proof-artifact-document";
import {
  getProofArtifact,
  type ProofArtifact,
} from "@/lib/proof-artifact-api";

export function ProofArtifactPrintView({ artifactId }: { artifactId: string }) {
  const [artifact, setArtifact] = useState<ProofArtifact | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    getProofArtifact(artifactId)
      .then((result) => {
        if (!cancelled) setArtifact(result);
      })
      .catch((reason) => {
        if (!cancelled) {
          setError(
            reason instanceof Error
              ? reason.message
              : "CareerOS could not load this proof artifact.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [artifactId]);

  if (error) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#f6f7f2] p-6">
        <section className="max-w-lg rounded-[28px] border border-[#e2cfaa] bg-white p-8 text-center">
          <h1 className="text-2xl font-semibold text-[#17362d]">
            Print view unavailable
          </h1>
          <p className="mt-3 text-sm leading-6 text-[#6d7e77]">{error}</p>
          <Link
            className="mt-5 inline-flex rounded-full bg-[#173f35] px-5 py-2 text-sm font-semibold text-white"
            href="/proof-artifacts"
          >
            Back to Proof workspace
          </Link>
        </section>
      </main>
    );
  }

  if (!artifact) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#f6f7f2] p-6 text-sm text-[#587066]">
        Loading print-ready proof artifact…
      </main>
    );
  }

  const version = artifact.latest_version;
  return (
    <div className="proof-print-shell min-h-screen bg-[#e9ebe6] px-4 py-5 sm:px-8">
      <div className="proof-print-actions mx-auto mb-5 flex max-w-[8.5in] flex-wrap items-center justify-between gap-3 rounded-2xl border border-[#d7dfda] bg-white px-4 py-3">
        <div>
          <p className="text-xs font-semibold text-[#365247]">Saved version {version.version_number}</p>
          <p className="mt-0.5 text-[11px] text-[#7a8983]">
            Use your browser’s print dialog to save as PDF.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            className="rounded-full border border-[#c7d8cf] px-4 py-2 text-xs font-semibold text-[#35634f]"
            href="/proof-artifacts"
          >
            Back to workspace
          </Link>
          <button
            className="rounded-full bg-[#173f35] px-5 py-2 text-xs font-semibold text-white"
            onClick={() => window.print()}
            type="button"
          >
            Print or save as PDF
          </button>
        </div>
      </div>
      <article className="proof-print-sheet mx-auto min-h-[10in] max-w-[8.5in] bg-white px-[0.55in] py-[0.45in] shadow-[0_18px_55px_rgba(31,55,45,0.14)]">
        <ProofArtifactDocument content={version.content} />
        <footer className="mt-8 border-t border-[#dfe7e2] pt-3 text-[9px] leading-4 text-[#71817b]">
          <p>
            Source project: {artifact.source_memory_title} · {version.evidence_references.length} supporting reference
            {version.evidence_references.length === 1 ? "" : "s"}
          </p>
          {version.evidence_references.length > 0 && (
            <p className="mt-1">
              Evidence sources: {[
                ...new Set(version.evidence_references.map((item) => item.source_label)),
              ].join(", ")}
            </p>
          )}
        </footer>
      </article>
    </div>
  );
}
