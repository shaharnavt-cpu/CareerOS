"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { WorkspaceNav } from "@/components/common/workspace-nav";
import {
  convertProposalToEnrichment,
  createEnrichment,
  listEnrichments,
  updateEnrichment,
  type EnrichmentStatus,
  type MemoryEnrichment,
} from "@/lib/enrichment-api";
import {
  listEligibleProofMemories,
  type ProofMemoryOption,
} from "@/lib/proof-artifact-api";

type EnrichmentWorkspaceProps = {
  initialMemoryId?: string;
  proposalId?: string;
};

export function EnrichmentWorkspace({
  initialMemoryId,
  proposalId,
}: EnrichmentWorkspaceProps) {
  const [memories, setMemories] = useState<ProofMemoryOption[]>([]);
  const [enrichments, setEnrichments] = useState<MemoryEnrichment[]>([]);
  const [memoryId, setMemoryId] = useState(initialMemoryId ?? "");
  const [enrichmentText, setEnrichmentText] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftFields, setDraftFields] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState(
    "Loading approved Career Memory and enrichment proposals...",
  );

  const projectMemories = useMemo(() => {
    return memories.filter((memory) => memory.memory_type === "PROJECT");
  }, [memories]);
  const selectedMemory = projectMemories.find(
    (memory) => memory.id === memoryId,
  );

  useEffect(() => {
    let cancelled = false;
    Promise.all([listEligibleProofMemories(), listEnrichments()])
      .then(([memoryItems, enrichmentItems]) => {
        if (cancelled) return;
        const projects = memoryItems.filter(
          (memory) => memory.memory_type === "PROJECT",
        );
        const options = projects;
        setMemories(memoryItems);
        setEnrichments(enrichmentItems);
        if (
          initialMemoryId &&
          options.some((memory) => memory.id === initialMemoryId)
        ) {
          setMemoryId(initialMemoryId);
        } else if (options.length) {
          setMemoryId(options[0].id);
        }
        setNotice(
          options.length
            ? "Select an approved project and add deeper, source-backed detail."
            : "Approve a project memory before adding project evidence.",
        );
      })
      .catch((error) => {
        if (cancelled) return;
        setNotice(errorMessage(error));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [initialMemoryId]);

  function replaceEnrichment(updated: MemoryEnrichment) {
    setEnrichments((current) => [
      updated,
      ...current.filter((item) => item.id !== updated.id),
    ]);
  }

  async function generate() {
    if (!memoryId) {
      setNotice("Select an approved Career Memory before generating enrichment.");
      return;
    }
    if (!enrichmentText.trim()) {
      setNotice(
        "Paste project-specific context, methods, findings, or outputs first.",
      );
      return;
    }
    setBusyId("create");
    setNotice("Extracting source-backed project detail...");
    try {
      const created = await createEnrichment(memoryId, enrichmentText.trim());
      replaceEnrichment(created);
      setEnrichmentText("");
      setNotice(
        `CareerOS thinks this belongs to ${created.target_memory.title}. Review it before approval.`,
      );
    } catch (error) {
      setNotice(errorMessage(error));
    } finally {
      setBusyId(null);
    }
  }

  async function convertProposal() {
    if (!memoryId || !proposalId) return;
    setBusyId(proposalId);
    setNotice("Converting the duplicate project draft into enrichment...");
    try {
      const converted = await convertProposalToEnrichment(memoryId, proposalId);
      replaceEnrichment(converted);
      setNotice(
        `Duplicate draft converted. Review the proposed details for ${converted.target_memory.title}.`,
      );
    } catch (error) {
      setNotice(errorMessage(error));
    } finally {
      setBusyId(null);
    }
  }

  async function changeStatus(
    enrichment: MemoryEnrichment,
    status: EnrichmentStatus,
  ) {
    setBusyId(enrichment.id);
    try {
      const updated = await updateEnrichment(enrichment.id, { status });
      replaceEnrichment(updated);
      setNotice(
        status === "APPROVED"
          ? `Approved enrichment is now attached to ${updated.target_memory.title}. Regenerate its proof artifact to use the richer evidence.`
          : status === "REJECTED"
            ? "Rejected enrichment will not affect proof artifacts or diagnosis."
            : "Archived enrichment no longer guides proof artifacts or diagnosis.",
      );
    } catch (error) {
      setNotice(errorMessage(error));
    } finally {
      setBusyId(null);
    }
  }

  function startEditing(enrichment: MemoryEnrichment) {
    setEditingId(enrichment.id);
    setDraftFields(
      Object.fromEntries(
        Object.entries(enrichment.structured_enrichment).map(([key, value]) => [
          key,
          renderValue(value, "\n"),
        ]),
      ),
    );
  }

  async function saveEdit(enrichment: MemoryEnrichment) {
    setBusyId(enrichment.id);
    const structured = Object.fromEntries(
      Object.entries(draftFields)
        .filter(([, value]) => value.trim())
        .map(([key, value]) => [
          key,
          Array.isArray(enrichment.structured_enrichment[key])
            ? value
                .split("\n")
                .map((item) => item.trim())
                .filter(Boolean)
            : value.trim(),
        ]),
    );
    try {
      const updated = await updateEnrichment(enrichment.id, {
        structured_enrichment: structured,
        status: enrichment.status === "PROPOSED" ? undefined : "PROPOSED",
      });
      replaceEnrichment(updated);
      setEditingId(null);
      setNotice("Enrichment edits saved as proposed. Approval is still required.");
    } catch (error) {
      setNotice(errorMessage(error));
    } finally {
      setBusyId(null);
    }
  }

  const visibleEnrichments = enrichments.filter(
    (item) => !memoryId || item.target_memory.id === memoryId,
  );

  return (
    <div className="min-h-screen bg-[#f6f8f5] text-[#17362d]">
      <WorkspaceNav active="enrichment" />
      <main className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:py-14">
        <div className="border-b border-[#dbe3de] pb-8">
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-[#3e7d62]">
            Project evidence enrichment
          </p>
          <h1 className="mt-3 max-w-4xl text-4xl font-semibold tracking-[-0.045em] text-[#142f26] sm:text-5xl">
            Add deeper project evidence without creating duplicate memory.
          </h1>
          <p className="mt-4 max-w-3xl text-base leading-7 text-[#667871]">
            Attach methods, findings, limitations, and outputs to an existing
            approved project. CareerOS keeps the enrichment proposed until you
            approve it.
          </p>
        </div>

        <div
          aria-live="polite"
          className="mt-6 rounded-2xl border border-[#cfe1d7] bg-[#edf7f1] px-4 py-3 text-sm text-[#3d6c59]"
        >
          {notice}
        </div>

        {proposalId && memoryId && (
          <section className="mt-6 rounded-[24px] border border-[#e7c987] bg-[#fff8e8] p-5">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#89631d]">
              Possible duplicate project draft
            </p>
            <p className="mt-2 text-sm leading-6 text-[#6f592c]">
              Convert this draft into enrichment for {selectedMemory?.title}. Its
              evidence will be preserved, and CareerOS will not create another
              project memory.
            </p>
            <button
              className="mt-4 rounded-full bg-[#765519] px-4 py-2 text-xs font-semibold text-white disabled:opacity-50"
              disabled={busyId === proposalId}
              onClick={() => void convertProposal()}
              type="button"
            >
              {busyId === proposalId
                ? "Converting..."
                : "Convert duplicate draft into enrichment"}
            </button>
          </section>
        )}

        <div className="mt-8 grid gap-6 lg:grid-cols-[0.86fr_1.14fr]">
          <section className="rounded-[26px] border border-[#dce4df] bg-white p-5 sm:p-6">
            <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-[#72847c]">
              Add deeper project evidence
            </p>
            <label className="mt-5 block text-sm font-semibold text-[#29483d]">
              Approved project memory
              <select
                className="mt-2 w-full rounded-xl border border-[#cfdcd5] bg-white px-3 py-3 text-sm outline-none focus:ring-4 focus:ring-[#dceee5]"
                disabled={loading || !projectMemories.length}
                onChange={(event) => setMemoryId(event.target.value)}
                value={memoryId}
              >
                {!projectMemories.length && <option value="">No approved projects</option>}
                {projectMemories.map((memory) => (
                  <option key={memory.id} value={memory.id}>
                    {memory.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="mt-5 block text-sm font-semibold text-[#29483d]">
              Project details
              <textarea
                className="mt-2 min-h-64 w-full rounded-xl border border-[#cfdcd5] px-3 py-3 text-sm leading-6 outline-none focus:ring-4 focus:ring-[#dceee5]"
                onChange={(event) => setEnrichmentText(event.target.value)}
                placeholder={
                  "Research question:\nData or inputs:\nMethods:\nFindings:\nLimitations:\nOutputs:"
                }
                value={enrichmentText}
              />
            </label>
            <p className="mt-3 text-xs leading-5 text-[#71827b]">
              Paste the abstract, methods, results, or project notes. CareerOS will
              not invent missing tools, findings, metrics, or outcomes.
            </p>
            <button
              className="mt-5 w-full rounded-full bg-[#173f35] px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-45"
              disabled={busyId === "create" || !projectMemories.length}
              onClick={() => void generate()}
              type="button"
            >
              {busyId === "create"
                ? "Generating enrichment proposal..."
                : "Generate enrichment proposal"}
            </button>
          </section>

          <section>
            <div className="flex items-end justify-between gap-4">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-[#72847c]">
                  Review enrichment
                </p>
                <h2 className="mt-1 text-2xl font-semibold text-[#17362d]">
                  Proposed and approved details
                </h2>
              </div>
              <span className="text-xs text-[#7c8c85]">
                {visibleEnrichments.length} record
                {visibleEnrichments.length === 1 ? "" : "s"}
              </span>
            </div>

            {!visibleEnrichments.length ? (
              <div className="mt-5 rounded-[24px] border border-dashed border-[#cbd8d1] bg-white p-7">
                <p className="font-semibold text-[#315246]">
                  This project still has resume-level detail only.
                </p>
                <p className="mt-2 text-sm leading-6 text-[#71827b]">
                  Paste an abstract, methods section, findings, or output description
                  to create a reviewed enrichment proposal.
                </p>
              </div>
            ) : (
              <div className="mt-5 space-y-4">
                {visibleEnrichments.map((enrichment) => (
                  <article
                    className="rounded-[24px] border border-[#dce4df] bg-white p-5 shadow-[0_16px_40px_-34px_rgba(23,63,53,0.8)]"
                    key={enrichment.id}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#4f7c69]">
                          Enrich {enrichment.target_memory.title}
                        </p>
                        <h3 className="mt-1 text-lg font-semibold text-[#1d4034]">
                          {label(enrichment.enrichment_type)}
                        </h3>
                      </div>
                      <span className={statusClass(enrichment.status)}>
                        {label(enrichment.status)}
                      </span>
                    </div>

                    <div className="mt-4 rounded-2xl border border-[#dce8e1] bg-[#f7faf7] p-4 text-sm leading-6 text-[#526960]">
                      <p className="font-semibold text-[#315849]">
                        CareerOS thinks this belongs to {enrichment.target_memory.title}
                      </p>
                      <p className="mt-1">{enrichment.reasoning}</p>
                      <p className="mt-2 text-xs text-[#71827b]">
                        {Math.round(enrichment.confidence * 100)}% confidence - {" "}
                        {enrichment.identity_resolution.reasons.join(" ")}
                      </p>
                    </div>

                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      {Object.entries(enrichment.structured_enrichment).map(
                        ([key, value]) => (
                          <label
                            className="rounded-xl border border-[#e0e7e2] p-3"
                            key={key}
                          >
                            <span className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#71847b]">
                              {label(key)}
                            </span>
                            {editingId === enrichment.id ? (
                              <textarea
                                className="mt-2 min-h-24 w-full rounded-lg border border-[#bfd2c8] p-2 text-xs leading-5 outline-none"
                                onChange={(event) =>
                                  setDraftFields((current) => ({
                                    ...current,
                                    [key]: event.target.value,
                                  }))
                                }
                                value={draftFields[key] ?? ""}
                              />
                            ) : (
                              <span className="mt-1 block text-xs leading-5 text-[#345248]">
                                {renderValue(value)}
                              </span>
                            )}
                          </label>
                        ),
                      )}
                    </div>

                    {enrichment.warnings.length > 0 && (
                      <div className="mt-4 rounded-xl border border-[#ead6a9] bg-[#fff8e8] p-3 text-xs leading-5 text-[#76541f]">
                        {enrichment.warnings.map((warning) => (
                          <p key={warning}>{warning}</p>
                        ))}
                      </div>
                    )}
                    <p className="mt-4 text-xs text-[#6f8179]">
                      {enrichment.proof_artifact_readiness_impact} Evidence references
                      remain linked internally.
                    </p>

                    <div className="mt-5 flex flex-wrap gap-2 border-t border-[#edf0ed] pt-4">
                      {editingId === enrichment.id ? (
                        <>
                          <button
                            className="rounded-full bg-[#245f4d] px-4 py-2 text-xs font-semibold text-white"
                            disabled={busyId === enrichment.id}
                            onClick={() => void saveEdit(enrichment)}
                            type="button"
                          >
                            Save enrichment edits
                          </button>
                          <button
                            className="rounded-full border border-[#d5dfda] px-4 py-2 text-xs font-semibold text-[#586d64]"
                            onClick={() => setEditingId(null)}
                            type="button"
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <>
                          {enrichment.status === "PROPOSED" && (
                            <button
                              className="rounded-full bg-[#e2f2e8] px-4 py-2 text-xs font-semibold text-[#28664d]"
                              disabled={busyId === enrichment.id}
                              onClick={() =>
                                void changeStatus(enrichment, "APPROVED")
                              }
                              type="button"
                            >
                              Approve enrichment
                            </button>
                          )}
                          <button
                            className="rounded-full border border-[#d5dfda] px-4 py-2 text-xs font-semibold text-[#586d64]"
                            onClick={() => startEditing(enrichment)}
                            type="button"
                          >
                            Edit
                          </button>
                          {enrichment.status === "PROPOSED" && (
                            <button
                              className="rounded-full px-4 py-2 text-xs font-semibold text-[#9a5c4e]"
                              disabled={busyId === enrichment.id}
                              onClick={() =>
                                void changeStatus(enrichment, "REJECTED")
                              }
                              type="button"
                            >
                              Reject
                            </button>
                          )}
                          {enrichment.status === "APPROVED" && (
                            <>
                              <Link
                                className="rounded-full bg-[#173f35] px-4 py-2 text-xs font-semibold text-white"
                                href={`/proof-artifacts?source_memory_id=${enrichment.target_memory.id}`}
                              >
                                Regenerate proof artifact
                              </Link>
                              <button
                                className="rounded-full px-4 py-2 text-xs font-semibold text-[#7a6850]"
                                disabled={busyId === enrichment.id}
                                onClick={() =>
                                  void changeStatus(enrichment, "ARCHIVED")
                                }
                                type="button"
                              >
                                Archive
                              </button>
                            </>
                          )}
                        </>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}

function renderValue(value: unknown, separator = "; "): string {
  if (Array.isArray(value)) return value.map(String).join(separator);
  if (value && typeof value === "object") return JSON.stringify(value);
  return String(value ?? "");
}

function label(value: string): string {
  return value
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function statusClass(status: EnrichmentStatus): string {
  const color = {
    PROPOSED: "border-[#d8c58f] bg-[#fff8e8] text-[#80631e]",
    APPROVED: "border-[#a9d2bb] bg-[#eaf6ef] text-[#2e6a50]",
    REJECTED: "border-[#e2cbc4] bg-[#fbefeb] text-[#8c5549]",
    ARCHIVED: "border-[#d7dcd9] bg-[#f2f4f3] text-[#697770]",
  }[status];
  return `rounded-full border px-3 py-1 text-[10px] font-bold uppercase tracking-[0.1em] ${color}`;
}

function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "CareerOS could not update project evidence.";
}
