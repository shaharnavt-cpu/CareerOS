"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { WorkspaceNav } from "@/components/common/workspace-nav";
import { ProofArtifactDocument } from "@/components/proof-artifacts/proof-artifact-document";
import {
  createProofArtifact,
  listEligibleProofMemories,
  listProofArtifacts,
  regenerateProofArtifact,
  updateProofArtifact,
  updateProofArtifactVersion,
  type ProofArtifact,
  type ProofArtifactStatus,
  type ProofArtifactType,
  type ProofArtifactVersionUpdateInput,
  type ProofMemoryOption,
  type ProofTargetAudience,
} from "@/lib/proof-artifact-api";
import {
  proofArtifactStatusLabel,
  proofArtifactTypeLabel,
  proofAudienceLabel,
  proofReadinessLabel,
  proofVariantText,
} from "@/lib/proof-artifact-utils";

const artifactTypes: ProofArtifactType[] = [
  "CASE_STUDY",
  "GITHUB_README",
  "PORTFOLIO_PAGE",
  "APPLICATION_UPLOAD",
  "OUTREACH_SUMMARY",
  "INTERVIEW_STORY",
  "RESUME_BULLETS",
];

const targetAudiences: ProofTargetAudience[] = [
  "APPLICATION_UPLOAD",
  "PORTFOLIO",
  "GITHUB",
  "OUTREACH",
  "INTERVIEW_PREP",
  "GENERAL",
];

const variantLabels = [
  ["resume_bullets", "Resume bullets"],
  ["cover_letter_paragraph", "Cover letter paragraph"],
  ["outreach_blurb", "Outreach blurb"],
  ["interview_answer", "Interview answer"],
  ["github_readme_outline", "GitHub README outline"],
] as const;

type WorkspaceProps = {
  initialMemoryId?: string;
  initialDiagnosisResultId?: string;
  initialTargetRole?: string;
};

export function ProofArtifactWorkspace({
  initialMemoryId,
  initialDiagnosisResultId,
  initialTargetRole,
}: WorkspaceProps) {
  const [memories, setMemories] = useState<ProofMemoryOption[]>([]);
  const [artifacts, setArtifacts] = useState<ProofArtifact[]>([]);
  const [activeArtifact, setActiveArtifact] = useState<ProofArtifact | null>(null);
  const [memoryId, setMemoryId] = useState(initialMemoryId ?? "");
  const [targetRole, setTargetRole] = useState(initialTargetRole ?? "");
  const [artifactType, setArtifactType] =
    useState<ProofArtifactType>("CASE_STUDY");
  const [targetAudience, setTargetAudience] =
    useState<ProofTargetAudience>("APPLICATION_UPLOAD");
  const [loading, setLoading] = useState(true);
  const [memoryLoadFailed, setMemoryLoadFailed] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(
    "Loading approved Career Memory and saved proof artifacts…",
  );

  const selectedMemory = useMemo(
    () => memories.find((memory) => memory.id === memoryId) ?? null,
    [memories, memoryId],
  );

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([listEligibleProofMemories(), listProofArtifacts()]).then(
      ([memoryResult, artifactResult]) => {
        if (cancelled) return;
        const nextMemories =
          memoryResult.status === "fulfilled" ? memoryResult.value : [];
        const nextArtifacts =
          artifactResult.status === "fulfilled" ? artifactResult.value : [];
        const memoriesFailed = memoryResult.status === "rejected";
        const artifactsFailed = artifactResult.status === "rejected";
        const defaultArtifact =
          initialMemoryId || initialDiagnosisResultId
            ? null
            : (nextArtifacts.find((item) => item.status !== "ARCHIVED") ?? null);
        setMemoryLoadFailed(memoriesFailed);
        setMemories(nextMemories);
        setArtifacts(nextArtifacts);
        setActiveArtifact(defaultArtifact);

        if (initialMemoryId) {
          if (nextMemories.some((memory) => memory.id === initialMemoryId)) {
            setMemoryId(initialMemoryId);
          } else {
            setMemoryId("");
          }
        } else if (defaultArtifact) {
          setMemoryId(defaultArtifact.source_memory_id);
          setTargetRole(defaultArtifact.target_role);
          setArtifactType(defaultArtifact.artifact_type);
          setTargetAudience(defaultArtifact.target_audience);
        } else if (nextMemories.length) {
          setMemoryId(nextMemories[0].id);
        }

        if (memoriesFailed && artifactsFailed) {
          setLoadError("Approved memories and saved artifacts could not be loaded.");
          setNotice(
            "CareerOS could not load the Proof workspace. Check the backend and retry.",
          );
        } else if (memoriesFailed) {
          setLoadError("Approved memories could not be loaded.");
          setNotice(
            "CareerOS could not load approved memories. Saved artifacts remain available; retry before generating.",
          );
        } else if (artifactsFailed) {
          setLoadError("Saved proof artifacts could not be loaded.");
          setNotice(
            "Approved memories loaded, but saved proof artifacts are temporarily unavailable. You can retry or generate a new artifact.",
          );
        } else if (!nextMemories.length) {
          setLoadError("");
          setNotice("Approve career memories before building a proof artifact.");
        } else if (initialMemoryId && !nextMemories.some((item) => item.id === initialMemoryId)) {
          setNotice(
            "The suggested memory is not approved or no longer available. Choose an approved memory before generating.",
          );
        } else {
          setLoadError("");
          setNotice(
            defaultArtifact
              ? `Viewing saved artifact built from ${defaultArtifact.source_memory_title}. Change an input to start a new artifact.`
              : initialDiagnosisResultId
              ? "Diagnosis context loaded. Review the suggested memory and target before generating."
              : "Choose one approved memory and the audience that should recognize it.",
          );
        }
        setLoading(false);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [initialDiagnosisResultId, initialMemoryId]);

  function replaceArtifact(updated: ProofArtifact) {
    setArtifacts((current) => [
      updated,
      ...current.filter((artifact) => artifact.id !== updated.id),
    ]);
    setActiveArtifact(updated);
  }

  function startNewArtifact(message: string) {
    if (!activeArtifact) return;
    setActiveArtifact(null);
    setNotice(message);
  }

  async function generate() {
    if (!memoryId) {
      setNotice("Select an approved Career Memory before generating an artifact.");
      return;
    }
    if (!targetRole.trim()) {
      setNotice("Add a target role or program so the proof can be framed specifically.");
      return;
    }
    setBusy(true);
    setNotice("Packaging approved memory into role-specific proof…");
    try {
      const artifact = await createProofArtifact({
        source_memory_id: memoryId,
        target_role: targetRole.trim(),
        target_audience: targetAudience,
        artifact_type: artifactType,
        source_diagnosis_result_id:
          memoryId === initialMemoryId &&
          targetRole.trim() === initialTargetRole?.trim()
            ? initialDiagnosisResultId
            : undefined,
      });
      replaceArtifact(artifact);
      setNotice(
        "Proof artifact saved as a draft. Review its evidence, warnings, and wording before sharing.",
      );
    } catch (error) {
      setNotice(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function regenerate(artifact: ProofArtifact) {
    setBusy(true);
    setNotice("Generating a new version from the same approved memory…");
    try {
      const updated = await regenerateProofArtifact(artifact.id, {
        target_role: targetRole.trim() || artifact.target_role,
        target_audience: targetAudience,
        artifact_type: artifactType,
      });
      replaceArtifact(updated);
      setNotice(
        `Version ${updated.latest_version.version_number} saved. The previous version remains in history.`,
      );
    } catch (error) {
      setNotice(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function saveVersion(
    artifact: ProofArtifact,
    changes: ProofArtifactVersionUpdateInput,
  ): Promise<ProofArtifact> {
    try {
      const updated = await updateProofArtifactVersion(
        artifact.id,
        artifact.latest_version.id,
        changes,
      );
      replaceArtifact(updated);
      setNotice(
        "Edits saved. CareerOS rechecked the artifact for unsupported numeric claims.",
      );
      return updated;
    } catch (error) {
      setNotice(`Edits were not saved. ${errorMessage(error)}`);
      throw error;
    }
  }

  async function changeStatus(
    artifact: ProofArtifact,
    status: ProofArtifactStatus,
  ) {
    setBusy(true);
    try {
      const updated = await updateProofArtifact(artifact.id, { status });
      replaceArtifact(updated);
      setNotice(
        status === "READY"
          ? "Artifact marked ready. Its evidence and warnings remain visible for review."
          : status === "ARCHIVED"
            ? "Artifact archived. Its saved versions remain available."
            : "Artifact returned to draft status.",
      );
    } catch (error) {
      setNotice(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  function chooseArtifact(artifact: ProofArtifact) {
    setActiveArtifact(artifact);
    setMemoryId(artifact.source_memory_id);
    setTargetRole(artifact.target_role);
    setArtifactType(artifact.artifact_type);
    setTargetAudience(artifact.target_audience);
    setNotice(`Opened ${artifact.title}.`);
  }

  return (
    <div className="min-h-screen bg-[#f6f7f2]">
      <WorkspaceNav active="proof" />
      <main className="mx-auto max-w-[1500px] px-5 py-9 sm:px-8 lg:py-12">
        <header className="grid gap-6 border-b border-[#d7dfda] pb-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#3f8064]">
              Proof Artifact Builder
            </p>
            <h1 className="mt-3 max-w-3xl text-4xl font-semibold tracking-[-0.045em] text-[#142f26] sm:text-5xl">
              Make existing proof easy to recognize.
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-[#63766e]">
              Turn one approved Career Memory into a role-specific, submittable
              case study and supporting application variants.
            </p>
          </div>
          <div className="rounded-[24px] border border-[#cfe0d6] bg-[#eaf5ee] p-5">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#3f8064]">
              Evidence boundary
            </p>
            <p className="mt-2 text-sm leading-6 text-[#45665a]">
              Factual claims come from approved canonical memory. Outcome notes
              may guide framing, but remain strategy signals—not proof of skill or
              causality.
            </p>
          </div>
        </header>

        <div
          aria-live="polite"
          className="mt-5 rounded-2xl border border-[#d9e4de] bg-[#fbfcfa] px-4 py-3 text-sm text-[#587066]"
        >
          {notice}
        </div>
        {loadError && (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-[#e2cfaa] bg-[#fff9ed] px-4 py-3 text-sm text-[#76541f]">
            <span>{loadError}</span>
            <button
              className="rounded-full border border-[#d7bd8d] bg-white px-4 py-2 text-xs font-semibold"
              onClick={() => window.location.reload()}
              type="button"
            >
              Retry loading
            </button>
          </div>
        )}

        <div className="mt-6 grid gap-6 xl:grid-cols-[390px_minmax(0,1fr)] xl:items-start">
          <aside className="space-y-5 xl:sticky xl:top-5">
            <section className="rounded-[28px] border border-[#dce4df] bg-white p-5 sm:p-6">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7d8e87]">
                Artifact input
              </p>
              <h2 className="mt-1 text-xl font-semibold text-[#17362d]">
                Package one approved memory
              </h2>

              {!loading && memoryLoadFailed ? (
                <div className="mt-5 rounded-2xl border border-[#e2cfaa] bg-[#fff9ed] p-5">
                  <p className="font-semibold text-[#76541f]">
                    Approved memories are temporarily unavailable.
                  </p>
                  <p className="mt-2 text-sm leading-6 text-[#836b46]">
                    Retry loading before generating so CareerOS can enforce the approved-memory boundary.
                  </p>
                </div>
              ) : !loading && memories.length === 0 ? (
                <div className="mt-5 rounded-2xl border border-dashed border-[#cbd7d0] bg-[#fafbf8] p-5">
                  <p className="font-semibold text-[#365247]">
                    Approve career memories before building a proof artifact.
                  </p>
                  <p className="mt-2 text-sm leading-6 text-[#71817b]">
                    Proposed or rejected memories cannot be used as factual proof.
                  </p>
                  <Link
                    className="mt-4 inline-flex rounded-full bg-[#173f35] px-4 py-2 text-xs font-semibold text-white"
                    href="/review"
                  >
                    Review Career Memory
                  </Link>
                </div>
              ) : (
                <div className="mt-5 space-y-4">
                  <label className="block text-sm font-semibold text-[#365247]">
                    Approved memory
                    <select
                      className="mt-2 min-h-12 w-full rounded-2xl border border-[#cfdbd4] bg-[#fbfcfa] px-4 font-normal text-[#29483e] outline-none ring-[#dceee5] focus:ring-4"
                      disabled={loading || busy}
                      onChange={(event) => {
                        setMemoryId(event.target.value);
                        if (event.target.value !== activeArtifact?.source_memory_id) {
                          startNewArtifact(
                            "Source memory changed. Complete the settings below to generate a new artifact; saved artifacts remain in the list.",
                          );
                        }
                      }}
                      value={memoryId}
                    >
                      <option value="">Select approved memory</option>
                      {memories.map((memory) => (
                        <option key={memory.id} value={memory.id}>
                          {memory.title}
                        </option>
                      ))}
                    </select>
                  </label>
                  {selectedMemory && <MemorySummary memory={selectedMemory} />}
                  <label className="block text-sm font-semibold text-[#365247]">
                    Target role or program
                    <input
                      className="mt-2 min-h-12 w-full rounded-2xl border border-[#cfdbd4] bg-[#fbfcfa] px-4 font-normal text-[#29483e] outline-none ring-[#dceee5] placeholder:text-[#96a39d] focus:ring-4"
                      onChange={(event) => {
                        setTargetRole(event.target.value);
                        if (event.target.value !== activeArtifact?.target_role) {
                          startNewArtifact(
                            "Target changed. Generate to create a new artifact; the saved artifact remains in the list.",
                          );
                        }
                      }}
                      placeholder="Data Analytics / AI internship"
                      value={targetRole}
                    />
                  </label>
                  <label className="block text-sm font-semibold text-[#365247]">
                    Artifact type
                    <select
                      className="mt-2 min-h-12 w-full rounded-2xl border border-[#cfdbd4] bg-[#fbfcfa] px-4 font-normal text-[#29483e] outline-none"
                      onChange={(event) => {
                        const nextType = event.target.value as ProofArtifactType;
                        setArtifactType(nextType);
                        if (nextType !== activeArtifact?.artifact_type) {
                          startNewArtifact(
                            "Artifact type changed. Generate to create a new artifact; the saved artifact remains in the list.",
                          );
                        }
                      }}
                      value={artifactType}
                    >
                      {artifactTypes.map((option) => (
                        <option key={option} value={option}>
                          {proofArtifactTypeLabel(option)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="block text-sm font-semibold text-[#365247]">
                    Target channel
                    <select
                      className="mt-2 min-h-12 w-full rounded-2xl border border-[#cfdbd4] bg-[#fbfcfa] px-4 font-normal text-[#29483e] outline-none"
                      onChange={(event) => {
                        const nextAudience = event.target.value as ProofTargetAudience;
                        setTargetAudience(nextAudience);
                        if (nextAudience !== activeArtifact?.target_audience) {
                          startNewArtifact(
                            "Target channel changed. Generate to create a new artifact; the saved artifact remains in the list.",
                          );
                        }
                      }}
                      value={targetAudience}
                    >
                      {targetAudiences.map((option) => (
                        <option key={option} value={option}>
                          {proofAudienceLabel(option)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    className="min-h-12 w-full rounded-full bg-[#173f35] px-5 text-sm font-semibold text-white transition hover:bg-[#285b4a] disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={busy || loading || !memories.length}
                    onClick={() => void generate()}
                    type="button"
                  >
                    {busy ? "Building proof…" : "Generate proof artifact"}
                  </button>
                </div>
              )}
            </section>

            <SavedArtifacts
              activeId={activeArtifact?.id}
              artifacts={artifacts}
              onChoose={chooseArtifact}
            />
          </aside>

          {activeArtifact ? (
            <ArtifactOutput
              artifact={activeArtifact}
              busy={busy}
              key={`${activeArtifact.id}-${activeArtifact.latest_version.id}-${activeArtifact.latest_version.updated_at}`}
              onRegenerate={regenerate}
              onSave={saveVersion}
              onStatus={changeStatus}
            />
          ) : (
            <section className="rounded-[30px] border border-dashed border-[#cbd7d0] bg-white p-10 text-center lg:p-16">
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#3f8064]">
                Diagnosis → Proof Sprint → Proof Artifact
              </p>
              <h2 className="mx-auto mt-3 max-w-xl text-3xl font-semibold text-[#17362d]">
                Your one-page case study will appear here.
              </h2>
              <p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-[#6d7e77]">
                CareerOS will preserve the evidence linkage internally, identify
                unsupported claims, and create channel-specific variants from the
                same approved memory.
              </p>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}

function MemorySummary({ memory }: { memory: ProofMemoryOption }) {
  return (
    <div className="rounded-2xl border border-[#dfe7e2] bg-[#f8faf7] p-4 text-xs leading-5 text-[#60746b]">
      <p className="font-bold uppercase tracking-[0.12em] text-[#3f715b]">
        {memory.memory_type.replaceAll("_", " ")}
      </p>
      <p className="mt-1 font-semibold text-[#2d5043]">{memory.title}</p>
      <p className="mt-2">
        {memory.evidence_count} evidence reference
        {memory.evidence_count === 1 ? "" : "s"} · {Math.round(memory.confidence * 100)}%
        memory confidence
      </p>
      {memory.source_labels.length > 0 && (
        <p className="mt-1">Sources: {memory.source_labels.join(", ")}</p>
      )}
    </div>
  );
}

function SavedArtifacts({
  activeId,
  artifacts,
  onChoose,
}: {
  activeId?: string;
  artifacts: ProofArtifact[];
  onChoose: (artifact: ProofArtifact) => void;
}) {
  if (!artifacts.length) return null;
  return (
    <section className="rounded-[28px] border border-[#dce4df] bg-white p-5">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7d8e87]">
        Saved proof artifacts
      </p>
      <div className="mt-3 space-y-2">
        {artifacts.map((artifact) => (
          <button
            className={`w-full rounded-2xl border p-3 text-left transition ${
              activeId === artifact.id
                ? "border-[#8dbda5] bg-[#edf6f0]"
                : "border-[#e1e8e4] bg-[#fbfcfa] hover:border-[#b8cfc2]"
            }`}
            key={artifact.id}
            onClick={() => onChoose(artifact)}
            type="button"
          >
            <span className="block text-sm font-semibold leading-5 text-[#29483e]">
              {artifact.title}
            </span>
            <span className="mt-1 block text-[10px] font-bold uppercase tracking-[0.1em] text-[#6d8077]">
              {proofArtifactStatusLabel(artifact.status)} · Version {artifact.latest_version.version_number}
            </span>
            <span className="mt-1 block text-[11px] text-[#71817b]">
              From {artifact.source_memory_title}
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

function ArtifactOutput({
  artifact,
  busy,
  onRegenerate,
  onSave,
  onStatus,
}: {
  artifact: ProofArtifact;
  busy: boolean;
  onRegenerate: (artifact: ProofArtifact) => Promise<void>;
  onSave: (
    artifact: ProofArtifact,
    changes: ProofArtifactVersionUpdateInput,
  ) => Promise<ProofArtifact>;
  onStatus: (artifact: ProofArtifact, status: ProofArtifactStatus) => Promise<void>;
}) {
  const version = artifact.latest_version;
  const [content, setContent] = useState(version.content);
  const [saveLabel, setSaveLabel] = useState("Save version edits");
  const [saving, setSaving] = useState(false);
  const dirty = content !== version.content;

  async function save() {
    if (!content.trim() || !dirty || saving) return;
    setSaving(true);
    setSaveLabel("Saving…");
    try {
      await onSave(artifact, { content: content.trim() });
      setSaveLabel("Saved");
      window.setTimeout(() => setSaveLabel("Save version edits"), 1600);
    } catch {
      setSaveLabel("Save failed—retry");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-w-0 space-y-5">
      <div className="rounded-2xl border border-[#c9ddd2] bg-[#edf6f0] px-4 py-3 text-sm text-[#365f4e]">
        <span className="font-semibold">Viewing saved artifact.</span> Built from
        approved memory: {artifact.source_memory_title}
      </div>
      <section className="rounded-[28px] border border-[#dce4df] bg-white p-5 sm:p-7">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
          <div>
            <div className="flex flex-wrap gap-2">
              <StatusPill status={artifact.status} />
              <span className="rounded-full bg-[#edf3ef] px-3 py-1 text-[10px] font-bold uppercase tracking-[0.1em] text-[#60746b]">
                {proofArtifactTypeLabel(artifact.artifact_type)}
              </span>
              <span className="rounded-full bg-[#f2eef9] px-3 py-1 text-[10px] font-bold uppercase tracking-[0.1em] text-[#68558d]">
                {proofReadinessLabel(version.readiness_label)} · {Math.round(version.readiness_score * 100)}%
              </span>
            </div>
            <h2 className="mt-3 text-2xl font-semibold text-[#17362d]">
              {artifact.title}
            </h2>
            <p className="mt-2 text-sm leading-6 text-[#65776f]">
              For {artifact.target_role} · {proofAudienceLabel(artifact.target_audience)} ·
              Version {version.version_number} of {artifact.version_count}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className="rounded-full border border-[#c7d8cf] px-4 py-2 text-xs font-semibold text-[#35634f] disabled:opacity-50"
              disabled={busy || saving || dirty}
              onClick={() => void onRegenerate(artifact)}
              type="button"
            >
              Regenerate new version
            </button>
            {artifact.status !== "READY" && artifact.status !== "ARCHIVED" && (
              <button
                className="rounded-full bg-[#173f35] px-4 py-2 text-xs font-semibold text-white disabled:opacity-50"
                disabled={busy || saving || dirty}
                onClick={() => void onStatus(artifact, "READY")}
                type="button"
              >
                Mark as ready
              </button>
            )}
            {artifact.status !== "ARCHIVED" ? (
              <button
                className="rounded-full border border-[#d7d2ca] px-4 py-2 text-xs font-semibold text-[#71675b] disabled:opacity-50"
                disabled={busy || saving || dirty}
                onClick={() => void onStatus(artifact, "ARCHIVED")}
                type="button"
              >
                Archive
              </button>
            ) : (
              <button
                className="rounded-full border border-[#c7d8cf] px-4 py-2 text-xs font-semibold text-[#35634f] disabled:opacity-50"
                disabled={busy || saving || dirty}
                onClick={() => void onStatus(artifact, "DRAFT")}
                type="button"
              >
                Restore draft
              </button>
            )}
          </div>
        </div>
        {dirty && (
          <p className="mt-4 rounded-2xl bg-[#fff7e7] px-4 py-3 text-xs font-semibold text-[#76541f]">
            Save your edits before regenerating, changing status, or opening the print view.
          </p>
        )}
      </section>

      <section className="rounded-[28px] border border-[#dce4df] bg-[#ebece7] p-4 sm:p-7">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#65776f]">
              One-page artifact preview
            </p>
            <p className="mt-1 text-xs text-[#71817b]">
              Skimmable proof from approved Career Memory
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <CopyButton
              label={artifact.artifact_type === "CASE_STUDY" ? "Copy case study" : "Copy artifact"}
              value={content}
            />
            {!dirty ? (
              <Link
                className="rounded-full border border-[#b9ccc1] bg-white px-4 py-2 text-xs font-semibold text-[#35634f]"
                href={`/proof-artifacts/${artifact.id}/print`}
                rel="noreferrer"
                target="_blank"
              >
                Open print view
              </Link>
            ) : (
              <span className="rounded-full border border-[#d2d5d1] px-4 py-2 text-xs font-semibold text-[#858f8a]">
                Save before printing
              </span>
            )}
          </div>
        </div>
        <article className="proof-preview-sheet mx-auto max-w-[820px] rounded-sm bg-white px-6 py-8 shadow-[0_18px_50px_rgba(31,55,45,0.12)] sm:px-10 sm:py-11">
          <ProofArtifactDocument content={content} />
          <footer className="mt-8 border-t border-[#dfe7e2] pt-3 text-[10px] leading-4 text-[#7a8983]">
            Source project: {artifact.source_memory_title} · {version.evidence_references.length} supporting reference
            {version.evidence_references.length === 1 ? "" : "s"}
          </footer>
        </article>
      </section>

      <section className="rounded-[28px] border border-[#dce4df] bg-white p-5 sm:p-7">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7d8e87]">
              Edit generated text
            </p>
            <h3 className="mt-1 text-xl font-semibold text-[#17362d]">
              Keep the artifact accurate and recognizably yours
            </h3>
          </div>
          <button
            className="rounded-full bg-[#214f40] px-4 py-2 text-xs font-semibold text-white disabled:opacity-50"
            disabled={saving || !dirty || !content.trim()}
            onClick={() => void save()}
            type="button"
          >
            {saveLabel}
          </button>
        </div>
        <textarea
          aria-label="Proof artifact editor"
          className="mt-4 min-h-[460px] w-full resize-y rounded-2xl border border-[#cfdbd4] bg-[#fbfcfa] p-4 font-mono text-sm leading-6 text-[#344e44] outline-none ring-[#dceee5] focus:ring-4"
          disabled={saving}
          onChange={(event) => {
            setContent(event.target.value);
            setSaveLabel("Save version edits");
          }}
          value={content}
        />
      </section>

      <div className="grid gap-5 lg:grid-cols-2">
        <EvidencePanel artifact={artifact} />
        <WarningPanel artifact={artifact} />
      </div>

      <OutcomeSignalPanel artifact={artifact} />
      <SupportingVariants artifact={artifact} />
    </div>
  );
}

function StatusPill({ status }: { status: ProofArtifactStatus }) {
  const style = {
    DRAFT: "bg-[#fff1cf] text-[#82581c]",
    REVIEWED: "bg-[#e7eef8] text-[#3f6081]",
    READY: "bg-[#dff2e7] text-[#286247]",
    ARCHIVED: "bg-[#e9ece9] text-[#65716c]",
  }[status];
  return (
    <span className={`rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-[0.1em] ${style}`}>
      {proofArtifactStatusLabel(status)}
    </span>
  );
}

function EvidencePanel({ artifact }: { artifact: ProofArtifact }) {
  const version = artifact.latest_version;
  return (
    <section className="rounded-[26px] border border-[#dce4df] bg-white p-5">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#3f8064]">
        Evidence used
      </p>
      <h3 className="mt-1 text-lg font-semibold text-[#17362d]">
        Approved proof behind this artifact
      </h3>
      <div className="mt-4 space-y-3">
        {version.evidence_references.length ? (
          version.evidence_references.map((reference) => (
            <article
              className="rounded-2xl border border-[#e1e8e4] bg-[#fbfcfa] p-4"
              key={reference.evidence_id}
            >
              <p className="text-xs font-semibold text-[#365247]">
                {reference.source_label}
              </p>
              {reference.excerpt && (
                <div className="mt-2">
                  <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#84918b]">
                    Approved source excerpt
                  </p>
                  <p className="mt-1 text-xs leading-5 text-[#687a73]">
                    “{reference.excerpt}”
                  </p>
                </div>
              )}
            </article>
          ))
        ) : (
          <p className="rounded-2xl bg-[#fff7e7] p-4 text-sm leading-6 text-[#76541f]">
            This approved memory has no linked evidence IDs yet. The partial draft remains marked for evidence strengthening.
          </p>
        )}
      </div>
    </section>
  );
}

function WarningPanel({ artifact }: { artifact: ProofArtifact }) {
  const version = artifact.latest_version;
  return (
    <section className="rounded-[26px] border border-[#e2cfaa] bg-[#fff9ed] p-5">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#956b2d]">
        What not to claim
      </p>
      <h3 className="mt-1 text-lg font-semibold text-[#63481f]">
        Unsupported-claim safeguards
      </h3>
      <ul className="mt-4 space-y-3">
        {version.warnings.map((warning) => (
          <li className="flex gap-3 text-sm leading-6 text-[#72562c]" key={warning}>
            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[#b5873e]" />
            {warning}
          </li>
        ))}
      </ul>
      <div className="mt-5 rounded-2xl border border-[#ead9b8] bg-white/70 p-4">
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#8c682f]">
          Readiness assessment
        </p>
        <p className="mt-2 text-lg font-semibold text-[#63481f]">
          {proofReadinessLabel(version.readiness_label)} · {Math.round(version.readiness_score * 100)}%
        </p>
        <p className="mt-1 text-xs leading-5 text-[#836b46]">
          Readiness reflects evidence coverage and claim clarity. It is not an outcome prediction.
        </p>
      </div>
    </section>
  );
}

function OutcomeSignalPanel({ artifact }: { artifact: ProofArtifact }) {
  const signals = artifact.latest_version.outcome_signals;
  if (!signals.length) return null;
  return (
    <section className="rounded-[26px] border border-[#d9d2ec] bg-[#f7f4fc] p-5 sm:p-6">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#76609b]">
        Outcome signals · not canonical proof
      </p>
      <h3 className="mt-1 text-lg font-semibold text-[#33284a]">
        Approved strategy notes used separately
      </h3>
      <div className="mt-4 space-y-3">
        {signals.map((signal) => (
          <article
            className="rounded-2xl border border-[#e2dcf0] bg-white/80 p-4"
            key={signal.feedback_event_id}
          >
            <p className="text-sm font-semibold leading-6 text-[#4d4067]">
              {signal.summary}
            </p>
            <p className="mt-2 text-xs leading-5 text-[#665b7d]">
              Strategy guidance: {signal.guidance}
            </p>
            <p className="mt-2 text-xs leading-5 text-[#817694]">{signal.caveat}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function SupportingVariants({ artifact }: { artifact: ProofArtifact }) {
  const variants = artifact.latest_version.supporting_variants;
  return (
    <section className="rounded-[28px] border border-[#dce4df] bg-white p-5 sm:p-7">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7d8e87]">
        Supporting variants
      </p>
      <h3 className="mt-1 text-xl font-semibold text-[#17362d]">
        Reuse the same proof across channels
      </h3>
      <p className="mt-2 text-sm leading-6 text-[#6d7e77]">
        These drafts come from the same approved memory and artifact—not unrelated generated claims.
      </p>
      <p className="mt-1 text-xs leading-5 text-[#829089]">
        After a material edit to the primary artifact, regenerate when you want refreshed channel variants.
      </p>
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        {variantLabels.map(([key, label]) => {
          const value = proofVariantText(variants[key]);
          if (!value) return null;
          return (
            <article
              className="rounded-2xl border border-[#e0e7e3] bg-[#fbfcfa] p-4"
              key={key}
            >
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#567266]">
                  {label}
                </p>
                <CopyButton label={`Copy ${label.toLowerCase()}`} value={value} />
              </div>
              <p className="mt-3 whitespace-pre-line text-sm leading-6 text-[#5b6f66]">
                {value}
              </p>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function CopyButton({ label, value }: { label: string; value: string }) {
  const [copyLabel, setCopyLabel] = useState(label);
  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopyLabel("Copied");
    } catch {
      setCopyLabel("Copy unavailable");
    }
    window.setTimeout(() => setCopyLabel(label), 1600);
  }
  return (
    <button
      className="rounded-full border border-[#cbd9d1] bg-white px-3 py-1.5 text-[10px] font-bold text-[#4e7563]"
      onClick={() => void copy()}
      type="button"
    >
      {copyLabel}
    </button>
  );
}

function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "CareerOS could not complete that proof artifact action.";
}
