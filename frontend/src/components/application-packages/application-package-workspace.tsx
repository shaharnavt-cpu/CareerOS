"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { WorkspaceNav } from "@/components/common/workspace-nav";
import {
  createApplicationPackage,
  generateApplicationPackage,
  getApplicationPackage,
  listApplicationPackages,
  listEligibleApplicationPackageMemories,
  regenerateApplicationPackage,
  updateApplicationPackage,
  updateApplicationPackageOutputs,
  type ApplicationEvidenceTrace,
  type ApplicationEvidenceGroup,
  type ApplicationPackage,
  type ApplicationPackageListItem,
  type ApplicationPackageMemoryOption,
  type ApplicationPackageOutputs,
  type ApplicationPackageOutputsUpdateInput,
  type ApplicationQuestion,
  type ApplicationPackageStatus,
  type ApplicationPackageVersion,
  type ApplicationQualityReview,
  type ApplicationRequirementCoverage,
  type ApplicationSnippet,
  type ApplicationWarningGroups,
  type CoverLetterDraft,
  type PositioningSummary,
  type ResumeBulletGroup,
} from "@/lib/application-package-api";
import {
  applicationEvidenceSourceLabel,
  applicationEvidenceSupportLabel,
  applicationGenerationReasonLabel,
  applicationProviderLabel,
  applicationPackageCopyText,
  applicationPackageInputFingerprint,
  applicationPackageStatusLabel,
  applicationPackageVersionInput,
  applicationOpportunityRoleTitle,
  applicationWarningSeverityLabel,
  defaultRecommendedMemoryIds,
  moveSelectedMemory,
  normalizeApplicationPackageInput,
  packageMatchesInput,
  resumeApplicationClaimId,
  resumeBulletGroupText,
  snippetApplicationClaimId,
  splitPackageList,
  type ApplicationPackageInput,
} from "@/lib/application-package-utils";
import {
  getApplicationOpportunity,
  listApplicationOpportunities,
  type ApplicationOpportunity,
  type ApplicationOpportunityListItem,
} from "@/lib/application-api";
import { buildProofArtifactHref } from "@/lib/proof-artifact-utils";

type TargetForm = {
  opportunityId: string;
  roleTitle: string;
  company: string;
  location: string;
  jobType: string;
  targetDescription: string;
  requiredSkills: string;
  preferredSkills: string;
  responsibilities: string;
  applicationQuestions: ApplicationQuestion[];
};

type EditableOutputs = {
  positioning_summary: PositioningSummary;
  resume_bullets: ResumeBulletGroup[];
  cover_letter: CoverLetterDraft;
  application_snippets: ApplicationSnippet[];
};

const emptyTarget: TargetForm = {
  opportunityId: "",
  roleTitle: "",
  company: "",
  location: "",
  jobType: "",
  targetDescription: "",
  requiredSkills: "",
  preferredSkills: "",
  responsibilities: "",
  applicationQuestions: [],
};

export function ApplicationPackageWorkspace() {
  const [form, setForm] = useState<TargetForm>(emptyTarget);
  const [selectedMemoryIds, setSelectedMemoryIds] = useState<string[]>([]);
  const [memories, setMemories] = useState<ApplicationPackageMemoryOption[]>([]);
  const [opportunities, setOpportunities] = useState<
    ApplicationOpportunityListItem[]
  >([]);
  const [savedPackages, setSavedPackages] = useState<
    ApplicationPackageListItem[]
  >([]);
  const [activePackage, setActivePackage] =
    useState<ApplicationPackage | null>(null);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>("loading");
  const busyActionRef = useRef<string | null>("loading");
  const [memoryLoading, setMemoryLoading] = useState(false);
  const memoryRequestRef = useRef(0);
  const freshSelectionRef = useRef(true);
  const [reviewDirty, setReviewDirty] = useState(false);
  const [notice, setNotice] = useState(
    "Choose a target and explicitly select approved Career Memory. CareerOS will not turn job-posting language into facts.",
  );

  const currentInput = useMemo(
    () => packageInput(form, selectedMemoryIds),
    [form, selectedMemoryIds],
  );
  const currentFingerprint = applicationPackageInputFingerprint(currentInput);
  const currentFingerprintRef = useRef(currentFingerprint);
  currentFingerprintRef.current = currentFingerprint;

  const visiblePackage = useMemo(
    () =>
      activePackage && packageMatchesInput(activePackage, currentInput)
        ? activePackage
        : null,
    [activePackage, currentInput],
  );

  const activeTargetMatches = useMemo(
    () =>
      activePackage
        ? packageMatchesInput(
            { ...activePackage, is_stale: false },
            currentInput,
          )
        : false,
    [activePackage, currentInput],
  );

  useEffect(() => {
    let cancelled = false;
    async function hydrate() {
      const [memoryResult, opportunityResult, packageResult] =
        await Promise.allSettled([
          listEligibleApplicationPackageMemories(),
          listApplicationOpportunities(),
          listApplicationPackages(),
        ]);
      if (cancelled) return;
      if (memoryResult.status === "fulfilled") {
        setMemories(memoryResult.value);
        if (
          packageResult.status === "fulfilled" &&
          packageResult.value.length === 0 &&
          freshSelectionRef.current
        ) {
          setSelectedMemoryIds(defaultRecommendedMemoryIds(memoryResult.value));
        }
      }
      if (opportunityResult.status === "fulfilled") {
        setOpportunities(opportunityResult.value);
      }
      if (packageResult.status === "fulfilled") {
        setSavedPackages(packageResult.value);
        const latest = packageResult.value[0];
        if (latest) {
          try {
            const applicationPackage = await getApplicationPackage(
              latest.package_id,
            );
            if (cancelled) return;
            hydrateFromPackage(applicationPackage);
            setNotice(
              applicationPackage.is_stale
                ? "Loaded your latest package. Its approved-memory input changed, so regenerate before using it."
                : "Loaded your latest saved application package and its version history.",
            );
          } catch (error) {
            if (!cancelled) setNotice(errorMessage(error));
          }
        }
      }
      if (
        memoryResult.status === "rejected" ||
        opportunityResult.status === "rejected" ||
        packageResult.status === "rejected"
      ) {
        setNotice(
          "Some Application Package data could not load. You can retry after confirming the local API is running.",
        );
      }
      if (!cancelled) {
        busyActionRef.current = null;
        setBusyAction(null);
      }
    }
    void hydrate();
    return () => {
      cancelled = true;
    };
  }, []);

  function hydrateFromPackage(applicationPackage: ApplicationPackage) {
    freshSelectionRef.current = false;
    setForm({
      opportunityId: applicationPackage.opportunity_id ?? "",
      roleTitle: applicationPackage.role_title,
      company: applicationPackage.company ?? "",
      location: applicationPackage.location ?? "",
      jobType: applicationPackage.job_type ?? "",
      targetDescription: applicationPackage.target_description,
      requiredSkills: applicationPackage.required_skills.join("\n"),
      preferredSkills: applicationPackage.preferred_skills.join("\n"),
      responsibilities: applicationPackage.responsibilities.join("\n"),
      applicationQuestions: structuredClone(
        applicationPackage.application_questions,
      ),
    });
    setSelectedMemoryIds(applicationPackage.selected_memory_ids);
    setActivePackage(applicationPackage);
    setReviewDirty(false);
  }

  function restoreVersionInputs(applicationPackage: ApplicationPackage) {
    if (busyActionRef.current !== null) return;
    const version = applicationPackage.latest_version;
    if (!version) return;
    const input = applicationPackageVersionInput(version);
    setForm(targetFormFromPackageInput(input));
    setSelectedMemoryIds(input.selectedMemoryIds);
    setNotice(
      `Restored target and selected-memory order from immutable version ${version.version_number}.`,
    );
  }

  function blockDirtyChange(): boolean {
    if (!reviewDirty) return false;
    setNotice(
      "Save or undo the unsaved output edits before changing the target, selected proof, package, or linked opportunity.",
    );
    return true;
  }

  function beginBusyAction(action: string): boolean {
    if (busyActionRef.current !== null) return false;
    busyActionRef.current = action;
    setBusyAction(action);
    return true;
  }

  function finishBusyAction(action: string) {
    if (busyActionRef.current !== action) return;
    busyActionRef.current = null;
    setBusyAction(null);
  }

  function invalidate(message?: string) {
    if (!activePackage?.latest_version) return;
    setNotice(
      message ??
        "Target or selected proof changed—generate a new package. The saved version remains in history.",
    );
  }

  function updateTarget<Key extends keyof TargetForm>(
    key: Key,
    value: TargetForm[Key],
  ) {
    if (busyActionRef.current !== null || memoryLoading) return;
    if (blockDirtyChange()) return;
    if (
      key === "roleTitle" &&
      freshSelectionRef.current &&
      !activePackage
    ) {
      setSelectedMemoryIds([]);
    }
    setForm((current) => ({ ...current, [key]: value }));
    invalidate();
  }

  function updateSelection(next: string[]) {
    if (busyActionRef.current !== null || memoryLoading) return;
    if (blockDirtyChange()) return;
    freshSelectionRef.current = false;
    setSelectedMemoryIds(next);
    invalidate(
      "Selected proof or its order changed—generate a new package. CareerOS will keep every project boundary explicit.",
    );
  }

  function toggleMemory(memoryId: string) {
    if (!selectedMemoryIds.includes(memoryId) && selectedMemoryIds.length >= 4) {
      setNotice(
        "A focused draft can use at most four selected memories. Remove one before adding another.",
      );
      return;
    }
    updateSelection(
      selectedMemoryIds.includes(memoryId)
        ? selectedMemoryIds.filter((id) => id !== memoryId)
        : [...selectedMemoryIds, memoryId],
    );
  }

  async function refreshMemories(targetRole = form.roleTitle) {
    const requestId = ++memoryRequestRef.current;
    setMemoryLoading(true);
    try {
      const options = await listEligibleApplicationPackageMemories(targetRole);
      if (requestId !== memoryRequestRef.current) return;
      setMemories(options);
      let appliedDefaults = false;
      if (!activePackage && freshSelectionRef.current) {
        setSelectedMemoryIds(defaultRecommendedMemoryIds(options));
        appliedDefaults = true;
      }
      setNotice(
        targetRole.trim()
          ? appliedDefaults
            ? "Updated role-aware recommendations and selected the strongest focused set. Review the order before generating."
            : "Updated role-aware proof recommendations. Your explicit selection and order did not change."
          : "Updated the approved-memory list. Select and order the proof you want to use.",
      );
    } catch (error) {
      if (requestId === memoryRequestRef.current) setNotice(errorMessage(error));
    } finally {
      if (requestId === memoryRequestRef.current) setMemoryLoading(false);
    }
  }

  async function chooseOpportunity(opportunityId: string) {
    if (busyActionRef.current !== null || memoryLoading) return;
    if (blockDirtyChange()) return;
    if (!opportunityId) {
      updateTarget("opportunityId", "");
      setNotice(
        "Switched to a manual target. Existing target text is preserved for review.",
      );
      return;
    }
    const action = "opportunity";
    if (!beginBusyAction(action)) return;
    try {
      const opportunity = await getApplicationOpportunity(opportunityId);
      const next = targetFromOpportunity(
        opportunity,
        form.applicationQuestions,
      );
      setForm(next);
      invalidate(
        "Linked opportunity loaded. Review the detected target fields, then generate a new package from your explicitly selected proof.",
      );
      setNotice(
        "Linked opportunity loaded. Review the detected target fields; CareerOS did not change your selected memories.",
      );
      await refreshMemories(next.roleTitle);
    } catch (error) {
      setNotice(errorMessage(error));
    } finally {
      finishBusyAction(action);
    }
  }

  async function loadSavedPackage(packageId: string) {
    if (memoryLoading) return;
    if (blockDirtyChange()) return;
    const action = `load-${packageId}`;
    if (!beginBusyAction(action)) return;
    try {
      const applicationPackage = await getApplicationPackage(packageId);
      hydrateFromPackage(applicationPackage);
      setNotice(
        applicationPackage.is_stale
          ? "This package is preserved, but approved memory changed after generation. Regenerate before using or saving it as current."
          : `Loaded ${applicationPackage.display_name} with ${applicationPackage.version_count} saved version${applicationPackage.version_count === 1 ? "" : "s"}.`,
      );
      await refreshMemories(applicationPackage.role_title);
    } catch (error) {
      setNotice(errorMessage(error));
    } finally {
      finishBusyAction(action);
    }
  }

  function startNewPackage() {
    if (busyActionRef.current !== null || memoryLoading || blockDirtyChange()) return;
    setForm(emptyTarget);
    freshSelectionRef.current = true;
    setSelectedMemoryIds([]);
    setActivePackage(null);
    void refreshMemories("");
    setNotice(
      "New package started. Enter a target and explicitly choose an input order; target relevance still determines final emphasis.",
    );
  }

  async function refreshSavedPackages(showArchived = includeArchived) {
    const packages = await listApplicationPackages(showArchived);
    setSavedPackages(packages);
  }

  async function changeArchivedVisibility(showArchived: boolean) {
    if (memoryLoading) return;
    const action = "archived-visibility";
    if (!beginBusyAction(action)) return;
    try {
      const packages = await listApplicationPackages(showArchived);
      setIncludeArchived(showArchived);
      setSavedPackages(packages);
    } catch (error) {
      setNotice(errorMessage(error));
    } finally {
      finishBusyAction(action);
    }
  }

  async function generate() {
    if (memoryLoading) return;
    if (!currentInput.roleTitle.trim()) {
      setNotice("Enter the target role title before generating.");
      return;
    }
    if (!currentInput.selectedMemoryIds.length) {
      setNotice(
        "Select at least one approved Career Memory. Job text cannot serve as proof.",
      );
      return;
    }
    const incompleteQuestionIndex = currentInput.applicationQuestions.findIndex(
      (question) => !question.question_text.trim(),
    );
    if (incompleteQuestionIndex >= 0) {
      setNotice(
        `Enter question ${incompleteQuestionIndex + 1} or remove it before generating. Zero supplied questions is valid.`,
      );
      return;
    }
    const invalidLengthIndex = currentInput.applicationQuestions.findIndex(
      (question) =>
        question.maximum_length != null &&
        (!Number.isInteger(question.maximum_length) ||
          question.maximum_length < 20 ||
          question.maximum_length > 12_000),
    );
    if (invalidLengthIndex >= 0) {
      setNotice(
        `Question ${invalidLengthIndex + 1} needs a maximum length between 20 and 12,000 characters.`,
      );
      return;
    }
    if (reviewDirty) {
      blockDirtyChange();
      return;
    }
    const requestedFingerprint = currentFingerprint;
    const action = "generate";
    if (!beginBusyAction(action)) return;
    try {
      const normalized = normalizeApplicationPackageInput(currentInput);
      let packageId = activePackage?.package_id;
      if (packageId) {
        const updated = await updateApplicationPackage(packageId, {
          opportunity_id: normalized.opportunity_id,
          display_name: normalized.company
            ? `${normalized.role_title} — ${normalized.company}`
            : normalized.role_title,
          role_title: normalized.role_title,
          company: normalized.company,
          location: normalized.location,
          job_type: normalized.job_type,
          target_description: normalized.target_description,
          required_skills: normalized.required_skills,
          preferred_skills: normalized.preferred_skills,
          responsibilities: normalized.responsibilities,
          application_questions: normalized.application_questions,
          selected_memory_ids: normalized.selected_memory_ids,
        });
        setActivePackage(updated);
      } else {
        const created = await createApplicationPackage({
          opportunity_id: normalized.opportunity_id,
          role_title: normalized.role_title,
          company: normalized.company,
          location: normalized.location,
          job_type: normalized.job_type,
          target_description: normalized.target_description,
          required_skills: normalized.required_skills,
          preferred_skills: normalized.preferred_skills,
          responsibilities: normalized.responsibilities,
          application_questions: normalized.application_questions,
          selected_memory_ids: normalized.selected_memory_ids,
        });
        packageId = created.package_id;
        setActivePackage(created);
      }
      const generated = await generateApplicationPackage(packageId, {
        selected_memory_ids: normalized.selected_memory_ids,
        application_questions: normalized.application_questions,
      });
      setActivePackage(generated);
      await refreshSavedPackages();
      if (
        currentFingerprintRef.current === requestedFingerprint &&
        packageMatchesInput(generated, currentInput)
      ) {
        setNotice(
          `Application package version ${generated.latest_version?.version_number ?? generated.version_count} generated and saved from approved memory.`,
        );
      } else {
        setNotice(
          "Generation finished and the version was saved, but the target changed during the request. Generate again to see current output.",
        );
      }
    } catch (error) {
      setNotice(errorMessage(error));
    } finally {
      finishBusyAction(action);
    }
  }

  async function regenerate(applicationPackage: ApplicationPackage) {
    const requestedFingerprint = currentFingerprint;
    const action = "regenerate";
    if (!beginBusyAction(action)) return;
    try {
      const normalized = normalizeApplicationPackageInput(currentInput);
      const generated = await regenerateApplicationPackage(
        applicationPackage.package_id,
        {
          selected_memory_ids: normalized.selected_memory_ids,
          application_questions: normalized.application_questions,
        },
      );
      setActivePackage(generated);
      await refreshSavedPackages();
      setNotice(
        currentFingerprintRef.current === requestedFingerprint &&
          packageMatchesInput(generated, currentInput)
          ? `Regenerated and saved version ${generated.latest_version?.version_number}. Earlier versions remain unchanged.`
          : "Regeneration was saved, but inputs changed during the request. The response is hidden until you generate for the current target.",
      );
    } catch (error) {
      setNotice(errorMessage(error));
    } finally {
      finishBusyAction(action);
    }
  }

  async function saveOutputEdits(
    applicationPackage: ApplicationPackage,
    input: ApplicationPackageOutputsUpdateInput,
  ): Promise<ApplicationPackage> {
    const action = "save";
    if (!beginBusyAction(action)) return applicationPackage;
    try {
      const saved = await updateApplicationPackageOutputs(
        applicationPackage.package_id,
        input,
      );
      setActivePackage(saved);
      await refreshSavedPackages();
      setNotice(
        `Manual edits saved as immutable version ${saved.latest_version?.version_number}. The underlying Career Memory was not changed.`,
      );
      return saved;
    } catch (error) {
      setNotice(errorMessage(error));
      throw error;
    } finally {
      finishBusyAction(action);
    }
  }

  async function changeStatus(
    applicationPackage: ApplicationPackage,
    status: ApplicationPackageStatus,
  ) {
    const action = `status-${status}`;
    if (!beginBusyAction(action)) return;
    try {
      const saved = await updateApplicationPackage(
        applicationPackage.package_id,
        { status },
      );
      setActivePackage(saved);
      await refreshSavedPackages();
      setNotice(
        status === "ARCHIVED"
          ? "Package archived. Its version history remains preserved."
          : status === "READY"
            ? "Package marked ready after review."
            : "Package restored as a draft.",
      );
    } catch (error) {
      setNotice(errorMessage(error));
    } finally {
      finishBusyAction(action);
    }
  }

  const busy = busyAction !== null;
  const navigationBusy = busy || memoryLoading;
  const inputLocked = navigationBusy || reviewDirty;
  const stale = Boolean(activePackage?.latest_version && !visiblePackage);

  return (
    <div className="min-h-screen bg-[#f6f7f2]">
      <WorkspaceNav active="application-packages" />

      <main className="mx-auto max-w-[1500px] px-5 py-8 sm:px-8 lg:py-10">
        <section className="mb-6 rounded-[30px] border border-[#c9ddd2] bg-[#edf6f0] p-5 shadow-[0_18px_50px_-44px_rgba(23,63,53,0.9)] sm:p-7">
          <div className="flex flex-col justify-between gap-5 xl:flex-row xl:items-end">
            <div className="max-w-4xl">
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#3f8064]">
                Approved memory → reviewed application package
              </p>
              <h1 className="mt-3 text-4xl font-semibold tracking-[-0.045em] text-[#142f26] sm:text-5xl">
                Resume + Cover Letter Builder
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-[#567068]">
                Build a targeted package from the exact Career Memory you choose.
                Target text guides relevance; only approved memory and approved
                enrichment can support factual claims.
              </p>
            </div>
            <div className="max-w-md rounded-2xl border border-[#bcd4c7] bg-white/75 px-4 py-3 text-xs leading-5 text-[#466458]">
              <span className="font-semibold">Drafts require review.</span> Outcome
              feedback stays strategy-only, unsupported requirements stay visible,
              and generated text never overwrites canonical memory.
            </div>
          </div>
        </section>

        <div className="grid items-start gap-6 lg:grid-cols-[390px_minmax(0,1fr)]">
          <aside className="space-y-5 lg:sticky lg:top-5">
            <TargetPanel
              busy={navigationBusy}
              inputLocked={inputLocked}
              form={form}
              opportunities={opportunities}
              onChooseOpportunity={chooseOpportunity}
              onGenerate={generate}
              onNew={startNewPackage}
              onRefreshMemories={refreshMemories}
              onUpdate={updateTarget}
              selectedCount={selectedMemoryIds.length}
            />
            <MemorySelectionPanel
              disabled={inputLocked}
              loading={memoryLoading}
              memories={memories}
              onMove={(memoryId, direction) =>
                updateSelection(
                  moveSelectedMemory(selectedMemoryIds, memoryId, direction),
                )
              }
              onRefresh={() => void refreshMemories()}
              onToggle={toggleMemory}
              selectedIds={selectedMemoryIds}
            />
            <SavedPackagePanel
              activeId={activePackage?.package_id}
              busy={navigationBusy}
              includeArchived={includeArchived}
              reviewDirty={reviewDirty}
              onChoose={loadSavedPackage}
              onIncludeArchived={changeArchivedVisibility}
              packages={savedPackages}
            />
          </aside>

          <div className="min-w-0 space-y-5">
            <div
              aria-live="polite"
              className="rounded-2xl border border-[#cfe0d6] bg-white px-4 py-3 text-sm leading-6 text-[#3c6655]"
            >
              {notice}
            </div>
            {reviewDirty && (
              <div className="rounded-2xl border border-[#e2cfaa] bg-[#fff9ed] px-4 py-3 text-xs leading-5 text-[#76541f]">
                <span className="font-semibold">Output edits are unsaved.</span>{" "}
                Target fields, memory selection, New package, linked opportunities,
                and saved-package loading are locked until you save or undo those
                edits.
              </div>
            )}

            {stale && activePackage ? (
              <StalePackagePanel
                approvedMemoryChanged={activeTargetMatches}
                applicationPackage={activePackage}
                busy={busy}
                onRestoreInputs={() => restoreVersionInputs(activePackage)}
                onStatus={changeStatus}
              />
            ) : visiblePackage ? (
              <PackageReview
                applicationPackage={visiblePackage}
                busy={busy}
                key={`${visiblePackage.package_id}:${visiblePackage.latest_version?.id}:${visiblePackage.updated_at}`}
                memories={memories}
                onDirtyChange={setReviewDirty}
                onRegenerate={regenerate}
                onSave={saveOutputEdits}
                onStatus={changeStatus}
              />
            ) : busyAction === "loading" ? (
              <LoadingPackage />
            ) : (
              <EmptyPackageState
                hasRole={Boolean(form.roleTitle.trim())}
                selectedCount={selectedMemoryIds.length}
              />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function TargetPanel({
  busy,
  form,
  inputLocked,
  opportunities,
  onChooseOpportunity,
  onGenerate,
  onNew,
  onRefreshMemories,
  onUpdate,
  selectedCount,
}: {
  busy: boolean;
  form: TargetForm;
  inputLocked: boolean;
  opportunities: ApplicationOpportunityListItem[];
  onChooseOpportunity: (opportunityId: string) => Promise<void>;
  onGenerate: () => Promise<void>;
  onNew: () => void;
  onRefreshMemories: (targetRole?: string) => Promise<void>;
  onUpdate: <Key extends keyof TargetForm>(
    key: Key,
    value: TargetForm[Key],
  ) => void;
  selectedCount: number;
}) {
  const linkedOpportunityMissing =
    form.opportunityId &&
    !opportunities.some((opportunity) => opportunity.id === form.opportunityId);
  const inputClass =
    "mt-1.5 w-full rounded-xl border border-[#cfdbd4] bg-[#fbfcfa] px-3 py-2.5 text-sm text-[#344e44] outline-none ring-[#dceee5] focus:ring-4 disabled:opacity-60";

  return (
    <section className="rounded-[28px] border border-[#dce4df] bg-white p-5 shadow-[0_18px_45px_-40px_rgba(23,63,53,0.8)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#3f8064]">
            1 · Target opportunity
          </p>
          <h2 className="mt-1 text-xl font-semibold text-[#17362d]">
            Define the role
          </h2>
        </div>
        <button
          className="rounded-full border border-[#d3ddd7] px-3 py-1.5 text-[10px] font-bold text-[#65776f]"
          disabled={inputLocked}
          onClick={onNew}
          type="button"
        >
          New package
        </button>
      </div>

      <label className="mt-5 block text-xs font-semibold text-[#526a60]" htmlFor="package-opportunity">
        Link a saved opportunity (optional)
      </label>
      <select
        className={inputClass}
        disabled={inputLocked}
        id="package-opportunity"
        onChange={(event) => void onChooseOpportunity(event.target.value)}
        value={form.opportunityId}
      >
        <option value="">Manual target</option>
        {linkedOpportunityMissing && (
          <option value={form.opportunityId}>Historical linked opportunity</option>
        )}
        {opportunities.map((opportunity) => (
          <option key={opportunity.id} value={opportunity.id}>
            {opportunity.title}
            {opportunity.organization ? ` · ${opportunity.organization}` : ""}
          </option>
        ))}
      </select>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
        <LabeledInput
          disabled={inputLocked}
          id="package-role-title"
          label="Role title"
          onBlur={() => void onRefreshMemories(form.roleTitle)}
          onChange={(value) => onUpdate("roleTitle", value)}
          required
          value={form.roleTitle}
        />
        <LabeledInput
          disabled={inputLocked}
          id="package-company"
          label="Company"
          onChange={(value) => onUpdate("company", value)}
          value={form.company}
        />
        <LabeledInput
          disabled={inputLocked}
          id="package-location"
          label="Location"
          onChange={(value) => onUpdate("location", value)}
          value={form.location}
        />
        <LabeledInput
          disabled={inputLocked}
          id="package-job-type"
          label="Job type"
          onChange={(value) => onUpdate("jobType", value)}
          placeholder="Internship, full-time…"
          value={form.jobType}
        />
      </div>

      <LabeledTextarea
        disabled={inputLocked}
        id="package-job-description"
        label="Role / job description"
        minHeight="min-h-44"
        onChange={(value) => onUpdate("targetDescription", value)}
        placeholder="Paste the posting or describe the target. This is relevance context, not proof."
        value={form.targetDescription}
      />
      <LabeledTextarea
        disabled={inputLocked}
        id="package-required-skills"
        label="Required skills"
        onChange={(value) => onUpdate("requiredSkills", value)}
        placeholder="One per line, or comma-separated"
        value={form.requiredSkills}
      />
      <LabeledTextarea
        disabled={inputLocked}
        id="package-preferred-skills"
        label="Preferred skills"
        onChange={(value) => onUpdate("preferredSkills", value)}
        placeholder="One per line, or comma-separated"
        value={form.preferredSkills}
      />
      <LabeledTextarea
        disabled={inputLocked}
        id="package-responsibilities"
        label="Responsibilities"
        onChange={(value) => onUpdate("responsibilities", value)}
        placeholder="One per line, or comma-separated"
        value={form.responsibilities}
      />
      <ApplicationQuestionsEditor
        disabled={inputLocked}
        onChange={(questions) => onUpdate("applicationQuestions", questions)}
        questions={form.applicationQuestions}
      />

      <button
        className="mt-5 w-full rounded-full bg-[#173f35] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#285b4a] disabled:cursor-not-allowed disabled:opacity-45"
        disabled={inputLocked || !form.roleTitle.trim() || selectedCount === 0}
        onClick={() => void onGenerate()}
        type="button"
      >
        {busy ? "Working…" : "Generate package"}
      </button>
      <p className="mt-2 text-center text-[11px] leading-5 text-[#75867f]">
        {selectedCount
          ? `${selectedCount} approved memor${selectedCount === 1 ? "y" : "ies"} selected in explicit order.`
          : "Select at least one approved memory below to generate."}
      </p>
    </section>
  );
}

function LabeledInput({
  disabled = false,
  id,
  label,
  onBlur,
  onChange,
  placeholder,
  required,
  value,
}: {
  disabled?: boolean;
  id: string;
  label: string;
  onBlur?: () => void;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  value: string;
}) {
  return (
    <label className="block text-xs font-semibold text-[#526a60]" htmlFor={id}>
      {label}
      {required && <span className="text-[#a66e24]"> *</span>}
      <input
        className="mt-1.5 w-full rounded-xl border border-[#cfdbd4] bg-[#fbfcfa] px-3 py-2.5 text-sm text-[#344e44] outline-none ring-[#dceee5] focus:ring-4 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={disabled}
        id={id}
        onBlur={onBlur}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        value={value}
      />
    </label>
  );
}

function LabeledTextarea({
  disabled = false,
  id,
  label,
  minHeight = "min-h-20",
  onChange,
  placeholder,
  value,
}: {
  disabled?: boolean;
  id: string;
  label: string;
  minHeight?: string;
  onChange: (value: string) => void;
  placeholder?: string;
  value: string;
}) {
  return (
    <label className="mt-4 block text-xs font-semibold text-[#526a60]" htmlFor={id}>
      {label}
      <textarea
        className={`mt-1.5 w-full resize-y rounded-xl border border-[#cfdbd4] bg-[#fbfcfa] px-3 py-2.5 text-sm leading-5 text-[#344e44] outline-none ring-[#dceee5] focus:ring-4 disabled:cursor-not-allowed disabled:opacity-60 ${minHeight}`}
        disabled={disabled}
        id={id}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        value={value}
      />
    </label>
  );
}

function ApplicationQuestionsEditor({
  disabled,
  onChange,
  questions,
}: {
  disabled: boolean;
  onChange: (questions: ApplicationQuestion[]) => void;
  questions: ApplicationQuestion[];
}) {
  function updateQuestion(
    questionId: string,
    update: Partial<ApplicationQuestion>,
  ) {
    onChange(
      questions.map((question) =>
        question.question_id === questionId
          ? { ...question, ...update }
          : question,
      ),
    );
  }

  return (
    <div className="mt-5 border-t border-[#e0e7e3] pt-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold text-[#526a60]">
            Application questions
          </p>
          <p className="mt-1 text-[11px] leading-5 text-[#75867f]">
            Add only the questions the application actually asks. Zero questions
            produces zero answers.
          </p>
        </div>
        <button
          className="shrink-0 rounded-full border border-[#c7d8cf] px-3 py-1.5 text-[10px] font-bold text-[#35634f] disabled:opacity-45"
          disabled={disabled || questions.length >= 50}
          onClick={() => onChange([...questions, newApplicationQuestion()])}
          type="button"
        >
          Add question
        </button>
      </div>

      {questions.length ? (
        <div className="mt-4 space-y-3">
          {questions.map((question, index) => (
            <article
              className="rounded-2xl border border-[#dbe5df] bg-[#f8faf8] p-3"
              key={question.question_id}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#557566]">
                    Question {index + 1}
                  </p>
                  <p className="mt-1 break-all text-[10px] text-[#829089]">
                    Stable ID: {question.question_id}
                  </p>
                </div>
                <button
                  className="rounded-lg border border-[#e0d6ca] px-2 py-1 text-[10px] font-semibold text-[#80684d] disabled:opacity-45"
                  disabled={disabled}
                  onClick={() =>
                    onChange(
                      questions.filter(
                        (item) => item.question_id !== question.question_id,
                      ),
                    )
                  }
                  type="button"
                >
                  Remove
                </button>
              </div>

              <label
                className="mt-3 block text-[11px] font-semibold text-[#526a60]"
                htmlFor={`application-question-${question.question_id}`}
              >
                Question text <span className="text-[#a66e24]">*</span>
              </label>
              <textarea
                className="mt-1.5 min-h-24 w-full resize-y rounded-xl border border-[#cfdbd4] bg-white px-3 py-2.5 text-sm leading-5 text-[#344e44] outline-none ring-[#dceee5] focus:ring-4 disabled:opacity-60"
                disabled={disabled}
                id={`application-question-${question.question_id}`}
                onChange={(event) =>
                  updateQuestion(question.question_id, {
                    question_text: event.target.value,
                  })
                }
                placeholder="Paste the application question exactly as asked."
                value={question.question_text}
              />

              <label className="mt-3 flex items-center gap-2 text-[11px] font-semibold text-[#526a60]">
                <input
                  checked={question.required}
                  className="h-4 w-4 accent-[#173f35]"
                  disabled={disabled}
                  onChange={(event) =>
                    updateQuestion(question.question_id, {
                      required: event.target.checked,
                    })
                  }
                  type="checkbox"
                />
                Required answer
              </label>

              <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
                <label className="text-[11px] font-semibold text-[#526a60]">
                  Maximum length (optional)
                  <input
                    className="mt-1.5 w-full rounded-xl border border-[#cfdbd4] bg-white px-3 py-2 text-sm text-[#344e44] outline-none ring-[#dceee5] focus:ring-4 disabled:opacity-60"
                    disabled={disabled}
                    max={12_000}
                    min={20}
                    onChange={(event) => {
                      const value = Number.parseInt(event.target.value, 10);
                      updateQuestion(question.question_id, {
                        maximum_length: Number.isNaN(value) ? null : value,
                      });
                    }}
                    placeholder="Characters"
                    type="number"
                    value={question.maximum_length ?? ""}
                  />
                </label>
                <label className="text-[11px] font-semibold text-[#526a60]">
                  Response type (optional)
                  <input
                    className="mt-1.5 w-full rounded-xl border border-[#cfdbd4] bg-white px-3 py-2 text-sm text-[#344e44] outline-none ring-[#dceee5] focus:ring-4 disabled:opacity-60"
                    disabled={disabled}
                    maxLength={100}
                    onChange={(event) =>
                      updateQuestion(question.question_id, {
                        response_type: event.target.value || null,
                      })
                    }
                    placeholder="Short text, paragraph…"
                    value={question.response_type ?? ""}
                  />
                </label>
              </div>

              <RequirementIdEditor
                disabled={disabled}
                ids={question.relevant_target_requirement_ids ?? []}
                onChange={(ids) =>
                  updateQuestion(question.question_id, {
                    relevant_target_requirement_ids: ids,
                  })
                }
                questionId={question.question_id}
              />
            </article>
          ))}
        </div>
      ) : (
        <p className="mt-4 rounded-xl border border-dashed border-[#d7e0db] p-3 text-xs leading-5 text-[#71817b]">
          No application questions supplied. Generation will return no application
          answers.
        </p>
      )}
    </div>
  );
}

function RequirementIdEditor({
  disabled,
  ids,
  onChange,
  questionId,
}: {
  disabled: boolean;
  ids: string[];
  onChange: (ids: string[]) => void;
  questionId: string;
}) {
  const [draft, setDraft] = useState("");

  function addId() {
    const value = draft.trim();
    if (!value || ids.includes(value)) return;
    onChange([...ids, value]);
    setDraft("");
  }

  return (
    <div className="mt-3">
      <label
        className="text-[11px] font-semibold text-[#526a60]"
        htmlFor={`application-question-requirement-${questionId}`}
      >
        Relevant target requirement IDs (optional)
      </label>
      {ids.length ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {ids.map((id) => (
            <span
              className="inline-flex items-center gap-1 rounded-full bg-[#e8f1ec] px-2.5 py-1 text-[10px] font-semibold text-[#486b5b]"
              key={id}
            >
              {id}
              <button
                aria-label={`Remove requirement ${id}`}
                disabled={disabled}
                onClick={() => onChange(ids.filter((item) => item !== id))}
                type="button"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      ) : null}
      <div className="mt-2 flex gap-2">
        <input
          className="min-w-0 flex-1 rounded-xl border border-[#cfdbd4] bg-white px-3 py-2 text-xs text-[#344e44] outline-none ring-[#dceee5] focus:ring-4 disabled:opacity-60"
          disabled={disabled}
          id={`application-question-requirement-${questionId}`}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              addId();
            }
          }}
          placeholder="Requirement ID"
          value={draft}
        />
        <button
          className="rounded-xl border border-[#c7d8cf] px-3 py-2 text-[10px] font-bold text-[#35634f] disabled:opacity-45"
          disabled={disabled || !draft.trim() || ids.includes(draft.trim())}
          onClick={addId}
          type="button"
        >
          Add ID
        </button>
      </div>
    </div>
  );
}

function MemorySelectionPanel({
  disabled,
  loading,
  memories,
  onMove,
  onRefresh,
  onToggle,
  selectedIds,
}: {
  disabled: boolean;
  loading: boolean;
  memories: ApplicationPackageMemoryOption[];
  onMove: (memoryId: string, direction: -1 | 1) => void;
  onRefresh: () => void;
  onToggle: (memoryId: string) => void;
  selectedIds: string[];
}) {
  const memoryById = new Map(memories.map((memory) => [memory.id, memory]));
  const selectedSet = new Set(selectedIds);
  const recommended = memories
    .filter((memory) => memory.recommended === true && !selectedSet.has(memory.id))
    .sort(
      (left, right) =>
        (left.recommendation_rank ?? Number.MAX_SAFE_INTEGER) -
        (right.recommendation_rank ?? Number.MAX_SAFE_INTEGER),
    );
  const otherEligible = memories.filter(
    (memory) => memory.recommended !== true && !selectedSet.has(memory.id),
  );
  return (
    <section className="rounded-[28px] border border-[#dce4df] bg-white p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#3f8064]">
            2 · Approved proof
          </p>
          <h2 className="mt-1 text-xl font-semibold text-[#17362d]">
            Select and order memory
          </h2>
        </div>
        <button
          className="rounded-full border border-[#cbd9d1] px-3 py-1.5 text-[10px] font-bold text-[#4e7563] disabled:opacity-50"
          disabled={loading || disabled}
          onClick={onRefresh}
          type="button"
        >
          {loading ? "Updating…" : "Refresh"}
        </button>
      </div>
      <p className="mt-2 text-xs leading-5 text-[#71817b]">
        Recommendations follow target relevance. Only your checked IDs are used,
        and their exact input order is preserved in every version.
      </p>

      <div className="mt-4 rounded-2xl border border-[#bcd5c8] bg-[#edf6f0] p-3">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#3f715b]">
            Selected memories · input order
          </p>
          {selectedIds.length > 0 ? <ol className="mt-2 space-y-2">
            {selectedIds.map((memoryId, index) => {
              const memory = memoryById.get(memoryId);
              return (
                <li
                  className="flex items-center gap-2 rounded-xl border border-[#d3e4db] bg-white p-2"
                  key={memoryId}
                >
                  <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[#173f35] text-[10px] font-bold text-white">
                    {index + 1}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-xs font-semibold text-[#315145]">
                    {memory?.title ?? `Unavailable memory ${shortId(memoryId)}`}
                  </span>
                  <button
                    aria-label={`Move ${memory?.title ?? "memory"} earlier`}
                    className="rounded-lg border border-[#d6e0db] px-2 py-1 text-[10px] disabled:opacity-30"
                    disabled={disabled || index === 0}
                    onClick={() => onMove(memoryId, -1)}
                    type="button"
                  >
                    ↑
                  </button>
                  <button
                    aria-label={`Move ${memory?.title ?? "memory"} later`}
                    className="rounded-lg border border-[#d6e0db] px-2 py-1 text-[10px] disabled:opacity-30"
                    disabled={disabled || index === selectedIds.length - 1}
                    onClick={() => onMove(memoryId, 1)}
                    type="button"
                  >
                    ↓
                  </button>
                  <button
                    aria-label={`Remove ${memory?.title ?? "memory"}`}
                    className="rounded-lg border border-[#e0d6ca] px-2 py-1 text-[10px] text-[#80684d]"
                    disabled={disabled}
                    onClick={() => onToggle(memoryId)}
                    type="button"
                  >
                    Remove
                  </button>
                </li>
              );
            })}
          </ol> : <p className="mt-2 text-xs leading-5 text-[#64796f]">
            No memories selected. Choose 2–4 recommendations for a focused draft.
          </p>}
      </div>

      <div className="mt-4 max-h-[520px] space-y-4 overflow-y-auto pr-1">
        {memories.length ? (
          <>
            <MemoryOptionList
              disabled={disabled}
              emptyLabel="All recommended memories are already selected."
              label="Recommended for this target"
              memories={recommended}
              onToggle={onToggle}
              recommended
              selectedIds={selectedIds}
            />
            <MemoryOptionList
              disabled={disabled}
              emptyLabel="No additional eligible memories are available."
              label="Other eligible memories"
              memories={otherEligible}
              onToggle={onToggle}
              selectedIds={selectedIds}
            />
          </>
        ) : (
          <p className="rounded-2xl border border-dashed border-[#d4ddd8] p-4 text-xs leading-5 text-[#71817b]">
            No eligible approved memories are available yet. Approve Career Memory
            or retry after the API is running.
          </p>
        )}
      </div>
    </section>
  );
}

function MemoryOptionList({
  disabled,
  emptyLabel,
  label,
  memories,
  onToggle,
  recommended = false,
  selectedIds,
}: {
  disabled: boolean;
  emptyLabel: string;
  label: string;
  memories: ApplicationPackageMemoryOption[];
  onToggle: (memoryId: string) => void;
  recommended?: boolean;
  selectedIds: string[];
}) {
  return (
    <section>
      <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.12em] text-[#657c71]">
        {label}
      </p>
      {memories.length ? (
        <div className="space-y-2">
          {memories.map((memory, index) => {
            const checked = selectedIds.includes(memory.id);
            return (
              <label
                className={`block cursor-pointer rounded-2xl border p-3 transition ${
                  checked
                    ? "border-[#8dbda5] bg-[#edf6f0]"
                    : "border-[#e1e8e4] bg-[#fbfcfa] hover:border-[#b8cfc2]"
                }`}
                key={memory.id}
              >
                <span className="flex items-start gap-3">
                  <input
                    checked={checked}
                    className="mt-1 h-4 w-4 accent-[#173f35]"
                    disabled={disabled}
                    onChange={() => onToggle(memory.id)}
                    type="checkbox"
                  />
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold leading-5 text-[#29483e]">
                        {memory.title}
                      </span>
                      {recommended && (
                        <span className="rounded-full bg-[#e9efeb] px-2 py-0.5 text-[9px] font-bold uppercase tracking-[0.08em] text-[#3f715b]">
                          Recommended {memory.recommendation_rank ?? index + 1}
                        </span>
                      )}
                    </span>
                    {memory.target_reason && (
                      <span className="mt-1 block text-xs leading-5 text-[#4d6e60]">
                        {memory.target_reason}
                      </span>
                    )}
                    <span className="mt-1 block text-[10px] leading-4 text-[#788981]">
                      {memory.memory_type.replaceAll("_", " ")} · {memory.evidence_count}{" "}
                      evidence reference{memory.evidence_count === 1 ? "" : "s"} ·{" "}
                      {Math.round(memory.confidence * 100)}% memory confidence
                    </span>
                    {memory.source_labels.length > 0 && (
                      <span className="mt-1 block truncate text-[10px] text-[#839088]">
                        Sources: {memory.source_labels.join(", ")}
                      </span>
                    )}
                  </span>
                </span>
              </label>
            );
          })}
        </div>
      ) : (
        <p className="rounded-xl border border-dashed border-[#d9e2dd] p-3 text-xs leading-5 text-[#71817b]">
          {emptyLabel}
        </p>
      )}
    </section>
  );
}

function SavedPackagePanel({
  activeId,
  busy,
  includeArchived,
  onChoose,
  onIncludeArchived,
  packages,
  reviewDirty,
}: {
  activeId?: string;
  busy: boolean;
  includeArchived: boolean;
  onChoose: (packageId: string) => Promise<void>;
  onIncludeArchived: (showArchived: boolean) => Promise<void>;
  packages: ApplicationPackageListItem[];
  reviewDirty: boolean;
}) {
  return (
    <section className="rounded-[28px] border border-[#dce4df] bg-white p-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7d8e87]">
            Saved package history
          </p>
          <h2 className="mt-1 text-lg font-semibold text-[#17362d]">
            Reopen a package
          </h2>
        </div>
        <label className="flex items-center gap-2 text-[10px] font-semibold text-[#687a72]">
          <input
            checked={includeArchived}
            className="accent-[#173f35]"
            disabled={busy}
            onChange={(event) =>
              void onIncludeArchived(event.target.checked)
            }
            type="checkbox"
          />
          Show archived
        </label>
      </div>
      <div className="mt-3 space-y-2">
        {packages.length ? (
          packages.map((applicationPackage) => (
            <button
              className={`w-full rounded-2xl border p-3 text-left transition disabled:opacity-60 ${
                activeId === applicationPackage.package_id
                  ? "border-[#8dbda5] bg-[#edf6f0]"
                  : "border-[#e1e8e4] bg-[#fbfcfa] hover:border-[#b8cfc2]"
              }`}
              disabled={busy || reviewDirty}
              key={applicationPackage.package_id}
              onClick={() => void onChoose(applicationPackage.package_id)}
              type="button"
            >
              <span className="block text-sm font-semibold leading-5 text-[#29483e]">
                {applicationPackage.display_name}
              </span>
              <span className="mt-1 block text-[10px] font-bold uppercase tracking-[0.09em] text-[#6d8077]">
                {applicationPackageStatusLabel(applicationPackage.status)} ·{" "}
                {applicationPackage.version_count} version
                {applicationPackage.version_count === 1 ? "" : "s"}
                {applicationPackage.is_stale ? " · stale" : ""}
              </span>
              <span className="mt-1 block text-[11px] text-[#71817b]">
                {applicationPackage.role_title}
                {applicationPackage.company
                  ? ` at ${applicationPackage.company}`
                  : ""}
              </span>
            </button>
          ))
        ) : (
          <p className="text-xs leading-5 text-[#7a8983]">
            No saved packages in this view yet.
          </p>
        )}
      </div>
    </section>
  );
}

function StalePackagePanel({
  approvedMemoryChanged,
  applicationPackage,
  busy,
  onRestoreInputs,
  onStatus,
}: {
  approvedMemoryChanged: boolean;
  applicationPackage: ApplicationPackage;
  busy: boolean;
  onRestoreInputs: () => void;
  onStatus: (
    applicationPackage: ApplicationPackage,
    status: ApplicationPackageStatus,
  ) => Promise<void>;
}) {
  return (
    <section className="rounded-[30px] border border-[#dfbd7b] bg-[#fff9ed] p-6 sm:p-8">
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#956b2d]">
        Saved output hidden · new draft required
      </p>
      <h2 className="mt-2 text-2xl font-semibold text-[#63481f]">
        {approvedMemoryChanged
          ? "Approved proof changed after this version was generated."
          : "Target or selected proof changed."}
      </h2>
      <p className="mt-3 max-w-2xl text-sm leading-7 text-[#72562c]">
        CareerOS will not present version {applicationPackage.latest_version?.version_number}{" "}
        as if it matches the current inputs. Generate a new version to refresh the
        package. The prior snapshot, evidence trace, warnings, and edits remain
        preserved in history.
      </p>
      <div className="mt-5 flex flex-wrap gap-3">
        {!approvedMemoryChanged && (
          <button
            className="rounded-full border border-[#d8bd8b] bg-white px-4 py-2 text-xs font-semibold text-[#76541f]"
            disabled={busy}
            onClick={onRestoreInputs}
            type="button"
          >
            Restore saved target inputs
          </button>
        )}
        {applicationPackage.status !== "ARCHIVED" ? (
          <button
            className="rounded-full border border-[#d8bd8b] bg-white px-4 py-2 text-xs font-semibold text-[#76541f]"
            disabled={busy}
            onClick={() => void onStatus(applicationPackage, "ARCHIVED")}
            type="button"
          >
            Archive package
          </button>
        ) : (
          <button
            className="rounded-full border border-[#d8bd8b] bg-white px-4 py-2 text-xs font-semibold text-[#76541f]"
            disabled={busy}
            onClick={() => void onStatus(applicationPackage, "DRAFT")}
            type="button"
          >
            Restore draft
          </button>
        )}
        <span className="rounded-full border border-[#e0c999] px-4 py-2 text-xs font-semibold text-[#80612e]">
          {applicationPackage.version_count} historical version
          {applicationPackage.version_count === 1 ? "" : "s"} preserved
        </span>
      </div>
      <CompactVersionHistory versions={applicationPackage.versions} />
      {applicationPackage.latest_version && (
        <details className="mt-4 rounded-2xl border border-[#d8bd8b] bg-white/80 p-4">
          <summary className="cursor-pointer text-xs font-semibold text-[#76541f]">
            Inspect preserved stale version {applicationPackage.latest_version.version_number}
          </summary>
          <div className="mt-4 border-t border-[#ead9b8] pt-4">
            {versionHasUserReviewClaims(applicationPackage.latest_version) && (
              <ClaimReviewCaveat dirty={false} />
            )}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#956b2d]">
                Historical snapshot only · not current output
              </p>
              <CopyButton
                label="Copy historical snapshot"
                value={applicationPackageCopyText(
                  applicationPackage.latest_version.outputs,
                )}
              />
            </div>
            <p className="mt-3 text-sm leading-6 text-[#72562c]">
              {
                applicationPackage.latest_version.outputs.positioning_summary
                  .primary_positioning
              }
            </p>
            <div className="mt-4 space-y-3">
              {applicationPackage.latest_version.outputs.resume_bullets.map(
                (group) => (
                  <div
                    className="rounded-xl border border-[#ead9b8] bg-white p-3"
                    key={group.memory_id}
                  >
                    <p className="text-xs font-semibold text-[#694d24]">
                      {group.memory_title}
                    </p>
                    <p className="mt-1 whitespace-pre-wrap text-xs leading-5 text-[#7a674c]">
                      {resumeBulletGroupText(group)}
                    </p>
                  </div>
                ),
              )}
            </div>
            <details className="mt-3 rounded-xl border border-[#ead9b8] bg-white p-3">
              <summary className="cursor-pointer text-xs font-semibold text-[#694d24]">
                Historical cover letter
              </summary>
              <p className="mt-3 whitespace-pre-wrap text-xs leading-6 text-[#7a674c]">
                {applicationPackage.latest_version.outputs.cover_letter.full_text}
              </p>
            </details>
          </div>
        </details>
      )}
    </section>
  );
}

function CompactVersionHistory({
  versions,
}: {
  versions: ApplicationPackageVersion[];
}) {
  return (
    <div className="mt-5 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
      {versions.slice(0, 6).map((version) => (
        <div
          className="rounded-2xl border border-[#ead9b8] bg-white/75 p-3"
          key={version.id}
        >
          <p className="text-xs font-semibold text-[#694d24]">
            Version {version.version_number} ·{" "}
            {applicationGenerationReasonLabel(version.generation_reason)}
          </p>
          <p className="mt-1 text-[10px] leading-4 text-[#846d48]">
            {dateTimeLabel(version.created_at)} · {version.selected_memory_ids.length}{" "}
            selected memor{version.selected_memory_ids.length === 1 ? "y" : "ies"}
          </p>
        </div>
      ))}
    </div>
  );
}

function EmptyPackageState({
  hasRole,
  selectedCount,
}: {
  hasRole: boolean;
  selectedCount: number;
}) {
  return (
    <section className="rounded-[30px] border border-dashed border-[#cbd7d0] bg-white p-10 text-center lg:p-16">
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#3f8064]">
        Target → approved proof → reviewable package
      </p>
      <h2 className="mx-auto mt-3 max-w-xl text-3xl font-semibold text-[#17362d]">
        Build the application from proof you can inspect.
      </h2>
      <p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-[#6d7e77]">
        {!hasRole
          ? "Enter a role or link a saved opportunity to begin."
          : selectedCount === 0
            ? "The target is ready. Now check at least one approved memory; CareerOS will never treat the job description as evidence."
            : `${selectedCount} approved memor${selectedCount === 1 ? "y is" : "ies are"} selected. Generate to create positioning, resume bullets, a cover letter, answers, traces, and warnings.`}
      </p>
    </section>
  );
}

function LoadingPackage() {
  return (
    <section className="rounded-[30px] border border-[#dce4df] bg-white p-10 text-center">
      <p className="text-sm font-semibold text-[#47675a]">
        Loading approved memory and saved packages…
      </p>
    </section>
  );
}

function PackageReview({
  applicationPackage,
  busy,
  memories,
  onDirtyChange,
  onRegenerate,
  onSave,
  onStatus,
}: {
  applicationPackage: ApplicationPackage;
  busy: boolean;
  memories: ApplicationPackageMemoryOption[];
  onDirtyChange: (dirty: boolean) => void;
  onRegenerate: (applicationPackage: ApplicationPackage) => Promise<void>;
  onSave: (
    applicationPackage: ApplicationPackage,
    input: ApplicationPackageOutputsUpdateInput,
  ) => Promise<ApplicationPackage>;
  onStatus: (
    applicationPackage: ApplicationPackage,
    status: ApplicationPackageStatus,
  ) => Promise<void>;
}) {
  const version = applicationPackage.latest_version!;
  const original = version.outputs;
  const [editor, setEditor] = useState<EditableOutputs>(() =>
    editableOutputsFrom(original),
  );
  const dirty = JSON.stringify(editor) !== JSON.stringify(editableOutputsFrom(original));
  const dirtyClaimIds = editedOutputClaimIds(original, editor);
  const reviewRequiredClaimIds = new Set(
    version.claim_ledger
      .filter(
        (claim) =>
          claim.user_edited || claim.support_level === "user_review_required",
      )
      .map((claim) => claim.claim_id),
  );
  const hasUserReviewClaims = reviewRequiredClaimIds.size > 0;
  const currentOutputs: ApplicationPackageOutputs = {
    ...original,
    ...editor,
  };

  useEffect(() => {
    onDirtyChange(dirty);
  }, [dirty, onDirtyChange]);

  async function save() {
    if (!dirty || busy) return;
    await onSave(applicationPackage, {
      ...editor,
      edit_summary:
        "Manual review edits to positioning, resume bullets, cover letter, or application answers.",
    });
  }

  function updatePositioning<Key extends keyof PositioningSummary>(
    key: Key,
    value: PositioningSummary[Key],
  ) {
    onDirtyChange(true);
    setEditor((current) => ({
      ...current,
      positioning_summary: {
        ...current.positioning_summary,
        [key]: value,
      },
    }));
  }

  function updateBullet(groupIndex: number, bulletIndex: number, value: string) {
    onDirtyChange(true);
    setEditor((current) => ({
      ...current,
      resume_bullets: current.resume_bullets.map((group, currentGroupIndex) =>
        currentGroupIndex !== groupIndex
          ? group
          : {
              ...group,
              bullets: group.bullets.map((bullet, currentBulletIndex) =>
                currentBulletIndex === bulletIndex
                  ? { ...bullet, bullet_text: value }
                  : bullet,
              ),
            },
      ),
    }));
  }

  function updateCoverLetter(value: string) {
    onDirtyChange(true);
    setEditor((current) => ({
      ...current,
      cover_letter: { ...current.cover_letter, full_text: value },
    }));
  }

  function updateSnippet(questionId: string, index: number, value: string) {
    onDirtyChange(true);
    setEditor((current) => ({
      ...current,
      application_snippets: current.application_snippets.map(
        (snippet, currentIndex) =>
          (questionId
            ? snippet.question_id === questionId
            : currentIndex === index)
            ? { ...snippet, text: value }
            : snippet,
      ),
    }));
  }

  return (
    <fieldset className="contents" disabled={busy}>
      <div className="space-y-5">
      <section className="rounded-[28px] border border-[#dce4df] bg-white p-5 sm:p-7">
        <div className="flex flex-col justify-between gap-5 xl:flex-row xl:items-start">
          <div className="min-w-0">
            <div className="flex flex-wrap gap-2">
              <PackageStatusPill status={applicationPackage.status} />
              <span className="rounded-full bg-[#edf3ef] px-3 py-1 text-[10px] font-bold uppercase tracking-[0.1em] text-[#60746b]">
                Version {version.version_number} of {applicationPackage.version_count}
              </span>
              <span className="rounded-full bg-[#f2eef9] px-3 py-1 text-[10px] font-bold uppercase tracking-[0.1em] text-[#68558d]">
                Draft from approved memory
              </span>
              {version.provider_metadata && (
                <span className="rounded-full bg-[#edf4fb] px-3 py-1 text-[10px] font-bold uppercase tracking-[0.1em] text-[#46667f]">
                  {applicationProviderLabel(version.provider_metadata)}
                </span>
              )}
              {hasUserReviewClaims && (
                <span className="rounded-full bg-[#fff0d6] px-3 py-1 text-[10px] font-bold uppercase tracking-[0.1em] text-[#8a5e22]">
                  User review required
                </span>
              )}
              {version.validation_summary?.status === "BLOCKED" && (
                <span className="rounded-full bg-[#fff0d6] px-3 py-1 text-[10px] font-bold uppercase tracking-[0.1em] text-[#8a5e22]">
                  Validation blocked
                </span>
              )}
            </div>
            <h2 className="mt-3 text-2xl font-semibold text-[#17362d] sm:text-3xl">
              {applicationPackage.display_name}
            </h2>
            <p className="mt-2 text-sm leading-6 text-[#65776f]">
              {applicationPackage.role_title}
              {applicationPackage.company
                ? ` at ${applicationPackage.company}`
                : ""}
              {applicationPackage.location
                ? ` · ${applicationPackage.location}`
                : ""}
              {applicationPackage.job_type
                ? ` · ${applicationPackage.job_type}`
                : ""}
            </p>
            <p className="mt-2 text-xs leading-5 text-[#829089]">
              Generated {dateTimeLabel(version.created_at)} with {version.generator_version}. Every generation and saved edit creates a preserved version.
            </p>
          </div>
          <div className="flex max-w-xl flex-wrap gap-2">
            <CopyButton
              disabled={dirty}
              disabledLabel="Save before copying"
              label="Copy full package"
              value={applicationPackageCopyText(currentOutputs)}
            />
            <button
              className="rounded-full border border-[#c7d8cf] px-4 py-2 text-xs font-semibold text-[#35634f] disabled:opacity-45"
              disabled={busy || dirty}
              onClick={() => void onRegenerate(applicationPackage)}
              type="button"
            >
              Regenerate new version
            </button>
            <button
              className="rounded-full bg-[#173f35] px-4 py-2 text-xs font-semibold text-white disabled:opacity-45"
              disabled={busy || !dirty}
              onClick={() => void save()}
              type="button"
            >
              Save edits
            </button>
            {applicationPackage.status !== "READY" &&
              applicationPackage.status !== "ARCHIVED" && (
                <button
                  className="rounded-full border border-[#a9c9b9] px-4 py-2 text-xs font-semibold text-[#35634f] disabled:opacity-45"
                  disabled={
                    busy ||
                    dirty ||
                    Boolean(
                      version.validation_summary &&
                        version.validation_summary.status !== "PASS",
                    )
                  }
                  onClick={() => void onStatus(applicationPackage, "READY")}
                  type="button"
                >
                  Mark ready
                </button>
              )}
            {applicationPackage.status !== "ARCHIVED" ? (
              <button
                className="rounded-full border border-[#d7d2ca] px-4 py-2 text-xs font-semibold text-[#71675b] disabled:opacity-45"
                disabled={busy || dirty}
                onClick={() => void onStatus(applicationPackage, "ARCHIVED")}
                type="button"
              >
                Archive package
              </button>
            ) : (
              <button
                className="rounded-full border border-[#c7d8cf] px-4 py-2 text-xs font-semibold text-[#35634f] disabled:opacity-45"
                disabled={busy || dirty}
                onClick={() => void onStatus(applicationPackage, "DRAFT")}
                type="button"
              >
                Restore draft
              </button>
            )}
          </div>
        </div>
        {dirty && (
          <div className="mt-5 rounded-2xl border border-[#e2cfaa] bg-[#fff9ed] px-4 py-3 text-xs leading-5 text-[#76541f]">
            <span className="font-semibold">Unsaved manual edits.</span> Save edits
            before regenerating or changing status. New factual wording requires
            evidence review and never becomes Career Memory automatically.
          </div>
        )}
        <SelectedProofStrip
          ids={version.selected_memory_ids}
          memories={memories}
          resumeGroups={original.resume_bullets}
        />
        <ProviderMetadataCard
          generationReason={version.generation_reason}
          metadata={version.provider_metadata}
        />
      </section>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
        <PositioningCard
          dirtyClaimIds={dirtyClaimIds}
          positioning={editor.positioning_summary}
          onChange={updatePositioning}
          reviewRequiredClaimIds={reviewRequiredClaimIds}
        />
        <WarningsCard
          applicationPackage={applicationPackage}
          warningGroups={applicationPackage.warning_groups}
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <RequirementCoverageCard
          coverage={version.requirement_coverage ?? applicationPackage.requirement_coverage}
        />
        <WritingQualityCard
          qualityReview={version.quality_review ?? applicationPackage.quality_review}
        />
      </div>

      <ResumeBulletsCard
        dirtyClaimIds={dirtyClaimIds}
        groups={editor.resume_bullets}
        onBulletChange={updateBullet}
        reviewRequiredClaimIds={reviewRequiredClaimIds}
      />

      <CoverLetterCard
        coverLetter={editor.cover_letter}
        dirty={dirtyClaimIds.has("cover-letter-full")}
        onChange={updateCoverLetter}
        reviewRequired={reviewRequiredClaimIds.has("cover-letter-full")}
      />

      <ApplicationSnippetsCard
        dirtyClaimIds={dirtyClaimIds}
        onChange={updateSnippet}
        reviewRequiredClaimIds={reviewRequiredClaimIds}
        snippets={editor.application_snippets}
      />

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
        <EvidenceTraceCard
          evidenceGroups={applicationPackage.evidence_groups}
          evidenceTrace={applicationPackage.evidence_trace}
          hasUserReviewClaims={hasUserReviewClaims || dirty}
          outcomeSignalCount={applicationPackage.outcome_signal_ids_used.length}
        />
        <ProofSuggestionsCard
          roleTitle={applicationPackage.role_title}
          suggestions={applicationPackage.suggested_proof_artifacts}
        />
      </div>

      <ReviewerQuestionsCard questions={applicationPackage.reviewer_questions} />
        <VersionHistoryCard applicationPackage={applicationPackage} />
      </div>
    </fieldset>
  );
}

function PackageStatusPill({ status }: { status: ApplicationPackageStatus }) {
  const style = {
    DRAFT: "bg-[#fff1cf] text-[#82581c]",
    READY: "bg-[#dff2e7] text-[#286247]",
    ARCHIVED: "bg-[#e9ece9] text-[#65716c]",
  }[status];
  return (
    <span
      className={`rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-[0.1em] ${style}`}
    >
      {applicationPackageStatusLabel(status)}
    </span>
  );
}

function SelectedProofStrip({
  ids,
  memories,
  resumeGroups,
}: {
  ids: string[];
  memories: ApplicationPackageMemoryOption[];
  resumeGroups: ResumeBulletGroup[];
}) {
  const memoryById = new Map(memories.map((memory) => [memory.id, memory.title]));
  for (const group of resumeGroups) memoryById.set(group.memory_id, group.memory_title);
  return (
    <div className="mt-5 rounded-2xl border border-[#d9e5de] bg-[#f7faf7] p-4">
      <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#4d705f]">
        Exact approved-memory boundary · selected input order
      </p>
      <ol className="mt-2 flex flex-wrap gap-2">
        {ids.map((id, index) => (
          <li
            className="rounded-full border border-[#c9ddd2] bg-white px-3 py-1.5 text-xs font-semibold text-[#365b4b]"
            key={id}
          >
            {index + 1}. {memoryById.get(id) ?? `Memory ${shortId(id)}`}
          </li>
        ))}
      </ol>
    </div>
  );
}

function ProviderMetadataCard({
  generationReason,
  metadata,
}: {
  generationReason: ApplicationPackageVersion["generation_reason"];
  metadata: ApplicationPackageVersion["provider_metadata"];
}) {
  if (!metadata) return null;
  const usage = [
    metadata.input_tokens != null ? `${metadata.input_tokens} input tokens` : null,
    metadata.cached_input_tokens != null
      ? `${metadata.cached_input_tokens} cached`
      : null,
    metadata.output_tokens != null ? `${metadata.output_tokens} output tokens` : null,
    metadata.latency_ms != null ? `${metadata.latency_ms} ms` : null,
  ].filter((value): value is string => Boolean(value));
  return (
    <div className="mt-4 rounded-2xl border border-[#d6e3ef] bg-[#f5f9fc] p-4 text-xs leading-5 text-[#4d6578]">
      <span className="font-semibold">
        {generationReason === "USER_EDIT"
          ? "Source generation provider:"
          : "Provider and model:"}
      </span>{" "}
      {applicationProviderLabel(metadata)}
      {usage.length > 0 && <span className="block mt-1 text-[#718496]">{usage.join(" · ")}</span>}
    </div>
  );
}

function RequirementCoverageCard({
  coverage,
}: {
  coverage: ApplicationRequirementCoverage | null | undefined;
}) {
  const groups: Array<{
    label: string;
    values: NonNullable<ApplicationRequirementCoverage["strongly_supported"]>;
    tone: string;
  }> = [
    {
      label: "Strong support",
      values: coverage?.strongly_supported ?? [],
      tone: "border-[#b8d8c7] bg-[#eff8f2] text-[#35634f]",
    },
    {
      label: "Partial support",
      values: coverage?.partially_supported ?? [],
      tone: "border-[#e6cf9d] bg-[#fff9ed] text-[#76541f]",
    },
    {
      label: "Missing proof",
      values: coverage?.unsupported ?? [],
      tone: "border-[#e1b9ae] bg-[#fff5f2] text-[#824e42]",
    },
    {
      label: "Not relevant enough",
      values: coverage?.not_relevant_enough ?? coverage?.not_relevant ?? [],
      tone: "border-[#d9ddda] bg-[#f5f6f4] text-[#65716c]",
    },
  ];
  if (!coverage) return null;
  return (
    <section className="rounded-[28px] border border-[#dce4df] bg-white p-5 sm:p-7">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#3f8064]">
        Requirement coverage
      </p>
      <h3 className="mt-1 text-xl font-semibold text-[#17362d]">
        What the selected proof can support
      </h3>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {groups.map((group) => (
          <div className={`rounded-2xl border p-3 ${group.tone}`} key={group.label}>
            <p className="text-[10px] font-bold uppercase tracking-[0.1em]">{group.label}</p>
            {group.values.length ? (
              <ul className="mt-2 space-y-2">
                {group.values.map((item) => (
                  <li className="text-xs leading-5" key={item.requirement}>
                    <span className="font-semibold">{item.requirement}</span>
                    {item.evidence?.length ? (
                      <span className="block opacity-85">{item.evidence.join(" · ")}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-xs leading-5 opacity-75">None listed.</p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function WritingQualityCard({
  qualityReview,
}: {
  qualityReview: ApplicationQualityReview | null | undefined;
}) {
  if (!qualityReview) return null;
  const checks: Array<[string, string | undefined]> = [
    ["Evidence", qualityReview.evidence_support],
    ["Role fit", qualityReview.role_relevance],
    ["Specificity", qualityReview.specificity],
    ["Naturalness", qualityReview.naturalness],
    ["Conciseness", qualityReview.concision],
    ["Recruiter readability", qualityReview.recruiter_readability],
    ["Genericness", qualityReview.genericness],
    ["Repetition", qualityReview.repetition],
    ["Overclaim risk", qualityReview.overclaim_risk],
  ].filter((entry): entry is [string, string] => Boolean(entry[1]));
  return (
    <section className="rounded-[28px] border border-[#d6e3ef] bg-[#f8fbfd] p-5 sm:p-7">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#52718f]">
        Writing-quality review
      </p>
      <h3 className="mt-1 text-xl font-semibold text-[#29465e]">
        Concise recruiter-facing check
      </h3>
      {qualityReview.primary_issue && (
        <p className="mt-3 rounded-xl border border-[#d9e3ec] bg-white p-3 text-sm leading-6 text-[#4d6578]">
          <span className="font-semibold">Primary issue:</span>{" "}
          {qualityReview.primary_issue}
        </p>
      )}
      <dl className="mt-4 grid gap-x-4 gap-y-3 sm:grid-cols-2">
        {checks.map(([label, value]) => (
          <div key={label}>
            <dt className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#688096]">{label}</dt>
            <dd className="mt-1 text-xs leading-5 text-[#4d6578]">{value}</dd>
          </div>
        ))}
      </dl>
      {qualityReview.notes?.length ? <SummaryList label="Review notes" values={qualityReview.notes} /> : null}
    </section>
  );
}

function PositioningCard({
  dirtyClaimIds,
  onChange,
  positioning,
  reviewRequiredClaimIds,
}: {
  dirtyClaimIds: ReadonlySet<string>;
  onChange: <Key extends keyof PositioningSummary>(
    key: Key,
    value: PositioningSummary[Key],
  ) => void;
  positioning: PositioningSummary;
  reviewRequiredClaimIds: ReadonlySet<string>;
}) {
  const primaryDirty = dirtyClaimIds.has("positioning-summary");
  const evidenceDirty = dirtyClaimIds.has("positioning-evidence");
  const primaryReviewRequired =
    primaryDirty || reviewRequiredClaimIds.has("positioning-summary");
  const evidenceReviewRequired =
    evidenceDirty || reviewRequiredClaimIds.has("positioning-evidence");
  return (
    <section className="rounded-[28px] border border-[#dce4df] bg-white p-5 sm:p-7">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#3f8064]">
            Positioning summary
          </p>
          <h3 className="mt-1 text-xl font-semibold text-[#17362d]">
            What to lead with
          </h3>
        </div>
        <CopyButton
          disabled={primaryDirty}
          disabledLabel="Save before copying"
          label="Copy positioning"
          value={positioning.primary_positioning}
        />
      </div>
      <label className="mt-5 block text-xs font-bold uppercase tracking-[0.1em] text-[#61766d]" htmlFor="positioning-primary">
        Primary positioning · editable
      </label>
      <textarea
        className="mt-2 min-h-28 w-full resize-y rounded-2xl border border-[#cfdbd4] bg-[#fbfcfa] p-4 text-sm leading-6 text-[#344e44] outline-none ring-[#dceee5] focus:ring-4"
        id="positioning-primary"
        onChange={(event) => onChange("primary_positioning", event.target.value)}
        value={positioning.primary_positioning}
      />
      {primaryReviewRequired && <ClaimReviewCaveat dirty={primaryDirty} />}
      <label className="mt-4 block text-xs font-bold uppercase tracking-[0.1em] text-[#61766d]" htmlFor="positioning-evidence">
        Strongest evidence · editable
      </label>
      <textarea
        className="mt-2 min-h-24 w-full resize-y rounded-2xl border border-[#cfdbd4] bg-[#fbfcfa] p-4 text-sm leading-6 text-[#344e44] outline-none ring-[#dceee5] focus:ring-4"
        id="positioning-evidence"
        onChange={(event) => onChange("strongest_evidence", event.target.value)}
        value={positioning.strongest_evidence}
      />
      {evidenceReviewRequired && <ClaimReviewCaveat dirty={evidenceDirty} />}
      <SummaryList label="Secondary evidence" values={positioning.secondary_evidence} />
      <SummaryList label="Recommended emphasis" values={positioning.recommended_emphasis} />
      <SummaryList label="Risks and gaps" values={positioning.risks_and_gaps} warning />
    </section>
  );
}

function SummaryList({
  label,
  values,
  warning = false,
}: {
  label: string;
  values: string[];
  warning?: boolean;
}) {
  if (!values.length) return null;
  return (
    <div className="mt-5">
      <p
        className={`text-[10px] font-bold uppercase tracking-[0.12em] ${warning ? "text-[#956b2d]" : "text-[#657c71]"}`}
      >
        {label}
      </p>
      <ul className="mt-2 space-y-2">
        {values.map((value) => (
          <li className="flex gap-2 text-sm leading-6 text-[#61736b]" key={value}>
            <span
              className={`mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full ${warning ? "bg-[#b5873e]" : "bg-[#60947a]"}`}
            />
            {value}
          </li>
        ))}
      </ul>
    </div>
  );
}

function WarningsCard({
  applicationPackage,
  warningGroups,
}: {
  applicationPackage: ApplicationPackage;
  warningGroups: ApplicationWarningGroups | undefined;
}) {
  const doNotClaim = applicationPackage.positioning_summary?.do_not_claim ?? [];
  const groupedWarnings = [
    ...(warningGroups?.partially_supported ?? []),
    ...(warningGroups?.unsupported ?? []),
    ...(warningGroups?.missing_proof ?? []),
  ];
  const groupedWarningKeys = new Set(
    groupedWarnings.map(
      (warning) =>
        `${warning.code}:${warning.requirement ?? ""}:${warning.message}`,
    ),
  );
  const ungroupedWarnings = applicationPackage.warnings.filter(
    (warning) =>
      !groupedWarningKeys.has(
        `${warning.code}:${warning.requirement ?? ""}:${warning.message}`,
      ),
  );
  const hasGroupedWarnings = groupedWarnings.length > 0;
  const hasWarnings =
    applicationPackage.warnings.length > 0 ||
    applicationPackage.unsupported_claims.length > 0 ||
    doNotClaim.length > 0 ||
    Boolean(
      warningGroups?.strongly_supported?.length ||
        warningGroups?.partially_supported?.length ||
        warningGroups?.unsupported?.length ||
        warningGroups?.missing_proof?.length,
    );
  return (
    <section className="rounded-[28px] border border-[#e2cfaa] bg-[#fff9ed] p-5 sm:p-7">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#956b2d]">
        Visible safeguards
      </p>
      <h3 className="mt-1 text-xl font-semibold text-[#63481f]">
        Warnings + do-not-claim list
      </h3>
      <p className="mt-2 text-xs leading-5 text-[#836b46]">
        Requested skills are not treated as supported skills. Resolve blocking
        warnings before marking a package ready.
      </p>
      {hasWarnings ? (
        <div className="mt-4 space-y-3">
          {warningGroups && (
            <GroupedWarnings warningGroups={warningGroups} />
          )}
          {ungroupedWarnings.map((warning, index) => (
            <article
              className={`rounded-2xl border p-4 ${
                warning.severity === "BLOCKING"
                  ? "border-[#d8a9a0] bg-[#fff3f0]"
                  : "border-[#ead9b8] bg-white/75"
              }`}
              key={`${warning.code}:${index}`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#8c682f]">
                  {applicationWarningSeverityLabel(warning.severity)}
                </span>
                {warning.requirement && (
                  <span className="rounded-full bg-[#f5ead4] px-2 py-0.5 text-[9px] font-semibold text-[#86602d]">
                    {warning.requirement}
                  </span>
                )}
              </div>
              <p className="mt-2 text-sm leading-6 text-[#72562c]">
                {warning.message}
              </p>
            </article>
          ))}
          {!hasGroupedWarnings && applicationPackage.unsupported_claims.map((claim) => (
            <div
              className="rounded-2xl border border-[#ead9b8] bg-white/75 p-4 text-sm leading-6 text-[#72562c]"
              key={claim}
            >
              <span className="font-semibold">Unsupported requirement:</span>{" "}
              {claim}
            </div>
          ))}
          {doNotClaim.map((claim) => (
            <div
              className="flex gap-3 rounded-2xl border border-[#ead9b8] bg-white/75 p-4 text-sm leading-6 text-[#72562c]"
              key={claim}
            >
              <span aria-hidden="true">×</span>
              <span>
                <span className="font-semibold">Do not claim:</span> {claim}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-4 rounded-2xl border border-[#ead9b8] bg-white/75 p-4 text-sm leading-6 text-[#72562c]">
          No package-level warning was emitted. Continue reviewing each claim and
          its evidence trace before use.
        </p>
      )}
    </section>
  );
}

function GroupedWarnings({
  warningGroups,
}: {
  warningGroups: ApplicationWarningGroups;
}) {
  const groups: Array<{
    label: string;
    warnings: ApplicationPackage["warnings"];
  }> = [
    { label: "Partially supported", warnings: warningGroups.partially_supported ?? [] },
    { label: "Unsupported", warnings: warningGroups.unsupported ?? [] },
    { label: "Missing proof", warnings: warningGroups.missing_proof ?? [] },
  ];
  return (
    <>
      {warningGroups.strongly_supported?.length ? (
        <SummaryList label="Strongly supported" values={warningGroups.strongly_supported} />
      ) : null}
      {groups.map((group) =>
        group.warnings.length ? (
          <div className="rounded-2xl border border-[#ead9b8] bg-white/75 p-4" key={group.label}>
            <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#8c682f]">{group.label}</p>
            <ul className="mt-2 space-y-2">
              {group.warnings.map((warning, index) => (
                <li className="text-sm leading-6 text-[#72562c]" key={`${warning.code}:${index}`}>
                  {warning.message}
                </li>
              ))}
            </ul>
          </div>
        ) : null,
      )}
    </>
  );
}

function ResumeBulletsCard({
  dirtyClaimIds,
  groups,
  onBulletChange,
  reviewRequiredClaimIds,
}: {
  dirtyClaimIds: ReadonlySet<string>;
  groups: ResumeBulletGroup[];
  onBulletChange: (
    groupIndex: number,
    bulletIndex: number,
    value: string,
  ) => void;
  reviewRequiredClaimIds: ReadonlySet<string>;
}) {
  return (
    <section className="rounded-[28px] border border-[#dce4df] bg-white p-5 sm:p-7">
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#3f8064]">
          Tailored resume bullets
        </p>
        <h3 className="mt-1 text-xl font-semibold text-[#17362d]">
          Specific proof, grouped by source memory
        </h3>
        <p className="mt-2 text-sm leading-6 text-[#6d7e77]">
          Edit wording here, then save a new immutable version. Preserved evidence
          is reference context—not validation—for any manually changed bullet.
        </p>
      </div>
      <div className="mt-5 space-y-5">
        {groups.map((group, groupIndex) => {
          const groupDirty = group.bullets.some((_, bulletIndex) =>
            dirtyClaimIds.has(resumeApplicationClaimId(groupIndex, bulletIndex)),
          );
          return (
          <article
            className="rounded-[24px] border border-[#dfe7e2] bg-[#fbfcfa] p-4 sm:p-5"
            key={group.memory_id}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#5b796b]">
                  {group.section_suggestion}
                </p>
                <h4 className="mt-1 text-lg font-semibold text-[#24483b]">
                  {group.memory_title}
                </h4>
                <p className="mt-1 max-w-3xl text-xs leading-5 text-[#71817b]">
                  Why it fits: {group.target_reason}
                </p>
              </div>
              <CopyButton
                disabled={groupDirty}
                disabledLabel="Save before copying"
                label={`Copy ${group.memory_title} bullets`}
                value={resumeBulletGroupText(group)}
              />
            </div>
            <div className="mt-4 space-y-4">
              {group.bullets.map((bullet, bulletIndex) => {
                const claimId = resumeApplicationClaimId(
                  groupIndex,
                  bulletIndex,
                );
                const bulletDirty = dirtyClaimIds.has(claimId);
                const reviewRequired =
                  bulletDirty || reviewRequiredClaimIds.has(claimId);
                return (
                <div
                  className="rounded-2xl border border-[#dfe7e2] bg-white p-4"
                  key={`${group.memory_id}:${bulletIndex}`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#657c71]">
                      Bullet {bulletIndex + 1} ·{" "}
                      {reviewRequired
                        ? "user review required"
                        : `${Math.round(bullet.confidence * 100)}% confidence`}
                    </span>
                    <CopyButton
                      disabled={bulletDirty}
                      disabledLabel="Save before copying"
                      label="Copy bullet"
                      value={bullet.bullet_text}
                    />
                  </div>
                  <textarea
                    aria-label={`${group.memory_title} resume bullet ${bulletIndex + 1}`}
                    className="mt-3 min-h-24 w-full resize-y rounded-xl border border-[#cfdbd4] bg-[#fbfcfa] p-3 text-sm leading-6 text-[#344e44] outline-none ring-[#dceee5] focus:ring-4"
                    onChange={(event) =>
                      onBulletChange(groupIndex, bulletIndex, event.target.value)
                    }
                    value={bullet.bullet_text}
                  />
                  {reviewRequired && <ClaimReviewCaveat dirty={bulletDirty} />}
                  <p className="mt-2 text-xs leading-5 text-[#71817b]">
                    <span className="font-semibold text-[#567266]">Why this bullet:</span>{" "}
                    {bullet.why_this_bullet}
                  </p>
                  {bullet.warnings.length > 0 && (
                    <ul className="mt-3 space-y-1 rounded-xl bg-[#fff7e7] p-3">
                      {bullet.warnings.map((warning) => (
                        <li className="text-xs leading-5 text-[#76541f]" key={warning}>
                          Warning: {warning}
                        </li>
                      ))}
                    </ul>
                  )}
                  <EvidenceDetails
                    preservedReference={reviewRequired}
                    traces={bullet.evidence_trace}
                  />
                </div>
                );
              })}
            </div>
          </article>
          );
        })}
      </div>
    </section>
  );
}

function CoverLetterCard({
  coverLetter,
  dirty,
  onChange,
  reviewRequired,
}: {
  coverLetter: CoverLetterDraft;
  dirty: boolean;
  onChange: (value: string) => void;
  reviewRequired: boolean;
}) {
  return (
    <section className="rounded-[28px] border border-[#dce4df] bg-white p-5 sm:p-7">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#3f8064]">
            Cover letter draft
          </p>
          <h3 className="mt-1 text-xl font-semibold text-[#17362d]">
            {dirty || reviewRequired
              ? "Manual draft with preserved reference context"
              : "Natural, target-aware, and evidence-bound"}
          </h3>
          <p className="mt-2 text-xs leading-5 text-[#71817b]">
            {coverLetter.subject_or_heading}
          </p>
        </div>
        <CopyButton
          disabled={dirty}
          disabledLabel="Save before copying"
          label="Copy cover letter"
          value={coverLetter.full_text}
        />
      </div>
      <textarea
        aria-label="Cover letter editor"
        className="mt-5 min-h-[430px] w-full resize-y rounded-2xl border border-[#cfdbd4] bg-[#fbfcfa] p-4 font-mono text-sm leading-7 text-[#344e44] outline-none ring-[#dceee5] focus:ring-4"
        onChange={(event) => onChange(event.target.value)}
        value={coverLetter.full_text}
      />
      {(dirty || reviewRequired) && <ClaimReviewCaveat dirty={dirty} />}
      <p className="mt-3 rounded-xl bg-[#f5f7f3] p-3 text-xs leading-5 text-[#71817b]">
        {dirty || reviewRequired
          ? "Paragraph traces reflect the generated snapshot. They are preserved reference context for manual wording and do not directly validate edits."
          : "Paragraph traces reflect the generated snapshot and show the support used for the generated wording."}
      </p>
      {coverLetter.warnings.length > 0 && (
        <SummaryList label="Cover letter warnings" values={coverLetter.warnings} warning />
      )}
      {coverLetter.strategy_notes.length > 0 && (
        <div className="mt-5 rounded-2xl border border-[#d9d2ec] bg-[#f7f4fc] p-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#76609b]">
            Strategy notes · not factual proof
          </p>
          <ul className="mt-2 space-y-2">
            {coverLetter.strategy_notes.map((note) => (
              <li className="text-sm leading-6 text-[#665b7d]" key={note}>
                {note}
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="mt-5 space-y-3">
        {coverLetter.evidence_trace_by_paragraph.map((paragraph) => (
          <details
            className="rounded-2xl border border-[#e0e7e3] bg-[#fbfcfa] p-4"
            key={paragraph.paragraph_label}
          >
            <summary className="cursor-pointer text-xs font-semibold text-[#46685a]">
              {paragraph.paragraph_label} evidence trace
            </summary>
            <p className="mt-3 text-xs leading-5 text-[#71817b]">
              {paragraph.paragraph_text}
            </p>
            <EvidenceTraceList
              compact
              preservedReference={dirty || reviewRequired}
              traces={paragraph.evidence_trace}
            />
          </details>
        ))}
      </div>
    </section>
  );
}

function ApplicationSnippetsCard({
  dirtyClaimIds,
  onChange,
  reviewRequiredClaimIds,
  snippets,
}: {
  dirtyClaimIds: ReadonlySet<string>;
  onChange: (questionId: string, index: number, value: string) => void;
  reviewRequiredClaimIds: ReadonlySet<string>;
  snippets: ApplicationSnippet[];
}) {
  const hasReviewRequiredSnippet = snippets.some((_, index) => {
    const claimId = snippetApplicationClaimId(index);
    return dirtyClaimIds.has(claimId) || reviewRequiredClaimIds.has(claimId);
  });
  return (
    <section className="rounded-[28px] border border-[#dce4df] bg-white p-5 sm:p-7">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#3f8064]">
        Application answer snippets
      </p>
      <h3 className="mt-1 text-xl font-semibold text-[#17362d]">
        {snippets.length === 0
          ? "No supplied questions"
          : hasReviewRequiredSnippet
            ? `${snippets.length} reviewable ${snippets.length === 1 ? "answer" : "answers"}`
            : `${snippets.length} copy-ready ${snippets.length === 1 ? "answer" : "answers"}`}
      </h3>
      {snippets.length ? (
      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        {snippets.map((snippet, index) => {
          const claimId = snippetApplicationClaimId(index);
          const dirty = dirtyClaimIds.has(claimId);
          const reviewRequired = dirty || reviewRequiredClaimIds.has(claimId);
          return (
          <article
            className="rounded-2xl border border-[#e0e7e3] bg-[#fbfcfa] p-4"
            key={snippet.question_id || `historical-answer-${index}`}
          >
            <div className="flex items-start justify-between gap-3">
              <h4 className="text-sm font-semibold leading-6 text-[#315145]">
                {snippet.question}
              </h4>
              <CopyButton
                disabled={dirty}
                disabledLabel="Save before copying"
                label="Copy answer"
                value={snippet.text}
              />
            </div>
            <textarea
              aria-label={`${snippet.question} answer editor`}
              className="mt-3 min-h-44 w-full resize-y rounded-xl border border-[#cfdbd4] bg-white p-3 text-sm leading-6 text-[#344e44] outline-none ring-[#dceee5] focus:ring-4"
              onChange={(event) =>
                onChange(snippet.question_id, index, event.target.value)
              }
              value={snippet.text}
            />
            {reviewRequired && <ClaimReviewCaveat dirty={dirty} />}
            {snippet.warnings.length > 0 && (
              <SummaryList label="Answer warnings" values={snippet.warnings} warning />
            )}
            <EvidenceDetails
              preservedReference={reviewRequired}
              traces={snippet.evidence_trace}
            />
          </article>
          );
        })}
      </div>
      ) : (
        <p className="mt-5 rounded-2xl border border-dashed border-[#d4ddd8] bg-[#fbfcfa] p-4 text-sm leading-6 text-[#71817b]">
          No application questions were supplied, so this package correctly
          contains zero application answers.
        </p>
      )}
    </section>
  );
}

function EvidenceTraceCard({
  evidenceGroups,
  evidenceTrace,
  hasUserReviewClaims,
  outcomeSignalCount,
}: {
  evidenceGroups: ApplicationEvidenceGroup[] | undefined;
  evidenceTrace: ApplicationEvidenceTrace[];
  hasUserReviewClaims: boolean;
  outcomeSignalCount: number;
}) {
  return (
    <section className="rounded-[28px] border border-[#dce4df] bg-white p-5 sm:p-7">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#3f8064]">
        Human-readable evidence trace
      </p>
      <h3 className="mt-1 text-xl font-semibold text-[#17362d]">
        {hasUserReviewClaims
          ? "Source context for package claims"
          : "Why these claims are supported"}
      </h3>
      <p className="mt-2 text-sm leading-6 text-[#6d7e77]">
        {hasUserReviewClaims
          ? "Manual wording requires review. These preserved sources are reference context, not claim-level validation for edited text."
          : "Proof, supported framing, strategy signals, and target relevance remain labeled as different kinds of input."}
      </p>
      {outcomeSignalCount > 0 && (
        <div className="mt-4 rounded-2xl border border-[#d9d2ec] bg-[#f7f4fc] p-4 text-sm leading-6 text-[#665b7d]">
          {outcomeSignalCount} approved outcome signal
          {outcomeSignalCount === 1 ? " is" : "s are"} included for strategy
          only—not as proof of a skill, result, or causality.
        </div>
      )}
      {evidenceGroups?.length ? (
        <>
          <EvidenceGroups groups={evidenceGroups} />
          <details className="mt-4 rounded-2xl border border-[#d9e5de] bg-[#f7faf7] p-4">
            <summary className="cursor-pointer text-xs font-semibold text-[#46685a]">
              Inspect full source-level trace ({evidenceTrace.length})
            </summary>
            <EvidenceTraceList
              compact
              preservedReference={hasUserReviewClaims}
              traces={evidenceTrace}
            />
          </details>
        </>
      ) : (
        <EvidenceTraceList
          preservedReference={hasUserReviewClaims}
          traces={evidenceTrace}
        />
      )}
    </section>
  );
}

function EvidenceGroups({ groups }: { groups: ApplicationEvidenceGroup[] }) {
  const memoryGroups = groups.filter((group) => group.memory_id).slice(0, 4);
  const visibleGroups = memoryGroups.length ? memoryGroups : groups.slice(0, 4);
  const labels: Array<[
    "direct_proof" | "approved_enrichment" | "supported_framing" | "strategy_signals" | "target_relevance",
    string,
  ]> = [
    ["direct_proof", "Direct proof"],
    ["approved_enrichment", "Approved enrichment"],
    ["supported_framing", "Supported framing"],
    ["strategy_signals", "Strategy signals"],
    ["target_relevance", "Target relevance"],
  ];
  return (
    <div className="mt-4 rounded-2xl border border-[#d9e5de] bg-[#f7faf7] p-4">
      <p className="text-xs font-semibold text-[#46685a]">
        Grouped evidence by selected memory ({visibleGroups.length})
      </p>
      <div className="mt-4 space-y-3">
        {visibleGroups.map((group, index) => (
          <article className="rounded-xl border border-[#dfe7e2] bg-white p-3" key={group.memory_id ?? `${group.memory_title}:${index}`}>
            <p className="text-xs font-semibold text-[#365247]">
              {group.memory_title ?? "Target-level context"}
            </p>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {labels.map(([field, label]) => {
                const values = group[field];
                return values?.length ? (
                  <div key={field}>
                    <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#657c71]">{label}</p>
                    <ul className="mt-1 space-y-1">
                      {values.map((value) => <li className="text-xs leading-5 text-[#61736b]" key={value}>{value}</li>)}
                    </ul>
                  </div>
                ) : null;
              })}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function ClaimReviewCaveat({ dirty }: { dirty: boolean }) {
  return (
    <p className="mt-3 rounded-xl border border-[#e2cfaa] bg-[#fff9ed] p-3 text-xs leading-5 text-[#76541f]">
      <span className="font-semibold">User review required.</span>{" "}
      {dirty
        ? "This unsaved wording has not been audited and cannot be copied yet. Save it to run the claim audit. "
        : "This saved manual wording is not directly validated. "}
      Preserved traces remain reference context only, not claim-level validation.
    </p>
  );
}

function EvidenceDetails({
  preservedReference = false,
  traces,
}: {
  preservedReference?: boolean;
  traces: ApplicationEvidenceTrace[];
}) {
  return (
    <details className="mt-3 rounded-xl border border-[#e1e8e4] bg-[#f8faf7] p-3">
      <summary className="cursor-pointer text-xs font-semibold text-[#4e7563]">
        Inspect evidence ({traces.length})
      </summary>
      <EvidenceTraceList
        compact
        preservedReference={preservedReference}
        traces={traces}
      />
    </details>
  );
}

function EvidenceTraceList({
  compact = false,
  preservedReference = false,
  traces,
}: {
  compact?: boolean;
  preservedReference?: boolean;
  traces: ApplicationEvidenceTrace[];
}) {
  if (!traces.length) {
    return (
      <p className="mt-3 rounded-xl bg-[#fff7e7] p-3 text-xs leading-5 text-[#76541f]">
        No supporting trace is attached to this item. Treat it as needing review.
      </p>
    );
  }
  return (
    <div className={compact ? "mt-3 space-y-2" : "mt-5 space-y-3"}>
      {preservedReference && (
        <p className="rounded-xl border border-[#e2cfaa] bg-[#fff9ed] p-3 text-xs font-semibold leading-5 text-[#76541f]">
          Preserved reference · not claim-level validation for edited wording
        </p>
      )}
      {traces.map((trace, index) => {
        const strategy = trace.source_type === "STRATEGY_SIGNAL";
        const targetContext = trace.source_type === "TARGET_CONTEXT";
        return (
          <article
            className={`rounded-2xl border p-4 ${
              strategy
                ? "border-[#d9d2ec] bg-[#f7f4fc]"
                : targetContext
                  ? "border-[#d9ddda] bg-[#f4f5f2]"
                  : "border-[#dfe7e2] bg-[#fbfcfa]"
            }`}
            key={`${trace.trace_id}:${index}`}
          >
            <div className="flex flex-wrap gap-2">
              <span
                className={`rounded-full px-2.5 py-1 text-[9px] font-bold uppercase tracking-[0.08em] ${
                  strategy
                    ? "bg-[#ebe5f5] text-[#6d5792]"
                    : targetContext
                      ? "bg-[#e6e9e6] text-[#66716c]"
                      : "bg-[#e3f0e8] text-[#3d7058]"
                }`}
              >
                {applicationEvidenceSourceLabel(trace.source_type)}
              </span>
              <span className="rounded-full border border-current/10 bg-white/70 px-2.5 py-1 text-[9px] font-bold uppercase tracking-[0.08em] text-[#65776f]">
                {preservedReference
                  ? "Reference only · edit requires review"
                  : applicationEvidenceSupportLabel(trace.support_type)}
              </span>
            </div>
            <p className="mt-3 text-sm font-semibold leading-6 text-[#365247]">
              {trace.source_label}
            </p>
            <p className="mt-1 text-xs leading-5 text-[#687a73]">{trace.detail}</p>
            {trace.caveat && (
              <p className="mt-2 text-xs font-semibold leading-5 text-[#7a674c]">
                Caveat: {trace.caveat}
              </p>
            )}
          </article>
        );
      })}
    </div>
  );
}

function ProofSuggestionsCard({
  roleTitle,
  suggestions,
}: {
  roleTitle: string;
  suggestions: ApplicationPackage["suggested_proof_artifacts"];
}) {
  return (
    <section className="rounded-[28px] border border-[#dce4df] bg-white p-5 sm:p-7">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#3f8064]">
        Suggested proof artifacts
      </p>
      <h3 className="mt-1 text-xl font-semibold text-[#17362d]">
        Strengthen optional uploads
      </h3>
      <div className="mt-4 space-y-3">
        {suggestions.length ? (
          suggestions.map((suggestion) => (
            <article
              className="rounded-2xl border border-[#e0e7e3] bg-[#fbfcfa] p-4"
              key={`${suggestion.memory_id}:${suggestion.artifact_title}`}
            >
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-[#567266]">
                {suggestion.action}
              </p>
              <h4 className="mt-1 text-sm font-semibold leading-6 text-[#315145]">
                {suggestion.artifact_title}
              </h4>
              <p className="mt-1 text-xs text-[#71817b]">
                From {suggestion.memory_title}
              </p>
              <p className="mt-2 text-sm leading-6 text-[#61736b]">
                {suggestion.reason}
              </p>
              <Link
                className="mt-3 inline-flex rounded-full border border-[#c7d8cf] bg-white px-3 py-1.5 text-[10px] font-bold text-[#4e7563]"
                href={
                  suggestion.artifact_id
                    ? `/proof-artifacts/${suggestion.artifact_id}/print`
                    : buildProofArtifactHref({
                        sourceMemoryId: suggestion.memory_id,
                        targetRole: roleTitle,
                      })
                }
              >
                {suggestion.artifact_id
                  ? "Open existing artifact"
                  : "Build this proof artifact"}
              </Link>
            </article>
          ))
        ) : (
          <p className="rounded-2xl border border-dashed border-[#d4ddd8] p-4 text-sm leading-6 text-[#71817b]">
            No proof artifact suggestion was generated for this package.
          </p>
        )}
      </div>
    </section>
  );
}

function ReviewerQuestionsCard({ questions }: { questions: string[] }) {
  return (
    <section className="rounded-[28px] border border-[#d5dfea] bg-[#f5f8fb] p-5 sm:p-7">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#52718f]">
        Reviewer questions
      </p>
      <h3 className="mt-1 text-xl font-semibold text-[#29465e]">
        Close evidence gaps before submitting
      </h3>
      <ol className="mt-4 grid gap-3 lg:grid-cols-2">
        {questions.length ? (
          questions.map((question, index) => (
            <li
              className="flex gap-3 rounded-2xl border border-[#d9e3ec] bg-white p-4 text-sm leading-6 text-[#4d6578]"
              key={question}
            >
              <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[#dfeaf3] text-[10px] font-bold text-[#46667f]">
                {index + 1}
              </span>
              {question}
            </li>
          ))
        ) : (
          <li className="rounded-2xl border border-[#d9e3ec] bg-white p-4 text-sm leading-6 text-[#4d6578]">
            No reviewer questions were generated. Continue checking the source
            trace for each claim.
          </li>
        )}
      </ol>
    </section>
  );
}

function VersionHistoryCard({
  applicationPackage,
}: {
  applicationPackage: ApplicationPackage;
}) {
  const latestId = applicationPackage.latest_version?.id;
  return (
    <section className="rounded-[28px] border border-[#dce4df] bg-white p-5 sm:p-7">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7d8e87]">
        Immutable version history
      </p>
      <h3 className="mt-1 text-xl font-semibold text-[#17362d]">
        Generated and edited snapshots
      </h3>
      <p className="mt-2 text-sm leading-6 text-[#6d7e77]">
        Earlier targets, selected-memory order, traces, warnings, and output text
        remain preserved. Expand an older version to inspect its content.
      </p>
      <div className="mt-5 space-y-3">
        {applicationPackage.versions.map((version) => {
          const role = snapshotString(version.target_snapshot.role_title);
          const company = snapshotString(version.target_snapshot.company);
          const latest = version.id === latestId;
          return (
            <details
              className="rounded-2xl border border-[#e0e7e3] bg-[#fbfcfa] p-4"
              key={version.id}
            >
              <summary className="cursor-pointer list-none">
                <span className="flex flex-wrap items-center justify-between gap-3">
                  <span>
                    <span className="block text-sm font-semibold text-[#315145]">
                      Version {version.version_number} ·{" "}
                      {applicationGenerationReasonLabel(version.generation_reason)}
                      {latest ? " · current" : ""}
                    </span>
                    <span className="mt-1 block text-[11px] text-[#71817b]">
                      {role || "Historical target"}
                      {company ? ` at ${company}` : ""} ·{" "}
                      {dateTimeLabel(version.created_at)}
                    </span>
                  </span>
                  <span className="rounded-full bg-[#edf3ef] px-3 py-1 text-[10px] font-bold text-[#60746b]">
                    {version.selected_memory_ids.length} memories ·{" "}
                    {version.warnings.length} warnings
                  </span>
                </span>
              </summary>
              <div className="mt-4 border-t border-[#e1e8e4] pt-4">
                {versionHasUserReviewClaims(version) && (
                  <ClaimReviewCaveat dirty={false} />
                )}
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="text-[10px] leading-5 text-[#7b8983]">
                    Generator: {version.generator_version}
                    <br />
                    Input fingerprint: {version.input_fingerprint.slice(0, 12)}…
                  </div>
                  <CopyButton
                    label={`Copy version ${version.version_number}`}
                    value={applicationPackageCopyText(version.outputs)}
                  />
                </div>
                {!latest && (
                  <div className="mt-4 space-y-4">
                    <div className="rounded-xl border border-[#e0e7e3] bg-white p-4">
                      <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#657c71]">
                        Historical positioning
                      </p>
                      <p className="mt-2 text-sm leading-6 text-[#526a60]">
                        {version.outputs.positioning_summary.primary_positioning}
                      </p>
                    </div>
                    <div className="rounded-xl border border-[#e0e7e3] bg-white p-4">
                      <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#657c71]">
                        Historical resume bullets
                      </p>
                      {version.outputs.resume_bullets.map((group) => (
                        <div className="mt-3" key={group.memory_id}>
                          <p className="text-xs font-semibold text-[#365247]">
                            {group.memory_title}
                          </p>
                          <p className="mt-1 whitespace-pre-wrap text-xs leading-5 text-[#687a73]">
                            {resumeBulletGroupText(group)}
                          </p>
                        </div>
                      ))}
                    </div>
                    <details className="rounded-xl border border-[#e0e7e3] bg-white p-4">
                      <summary className="cursor-pointer text-xs font-semibold text-[#46685a]">
                        Historical cover letter
                      </summary>
                      <p className="mt-3 whitespace-pre-wrap text-xs leading-6 text-[#687a73]">
                        {version.outputs.cover_letter.full_text}
                      </p>
                    </details>
                  </div>
                )}
              </div>
            </details>
          );
        })}
      </div>
    </section>
  );
}

function CopyButton({
  disabled = false,
  disabledLabel = "Copy unavailable",
  label,
  value,
}: {
  disabled?: boolean;
  disabledLabel?: string;
  label: string;
  value: string;
}) {
  const [copyLabel, setCopyLabel] = useState(label);
  async function copy() {
    if (disabled) return;
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
      className="shrink-0 rounded-full border border-[#cbd9d1] bg-white px-3 py-1.5 text-[10px] font-bold text-[#4e7563] disabled:cursor-not-allowed disabled:opacity-50"
      disabled={disabled}
      onClick={() => void copy()}
      type="button"
    >
      {disabled ? disabledLabel : copyLabel}
    </button>
  );
}

function editableOutputsFrom(outputs: ApplicationPackageOutputs): EditableOutputs {
  return {
    positioning_summary: structuredClone(outputs.positioning_summary),
    resume_bullets: structuredClone(outputs.resume_bullets),
    cover_letter: structuredClone(outputs.cover_letter),
    application_snippets: structuredClone(outputs.application_snippets),
  };
}

function editedOutputClaimIds(
  original: ApplicationPackageOutputs,
  editor: EditableOutputs,
): Set<string> {
  const ids = new Set<string>();
  if (
    editor.positioning_summary.primary_positioning !==
    original.positioning_summary.primary_positioning
  ) {
    ids.add("positioning-summary");
  }
  if (
    editor.positioning_summary.strongest_evidence !==
    original.positioning_summary.strongest_evidence
  ) {
    ids.add("positioning-evidence");
  }
  editor.resume_bullets.forEach((group, groupIndex) => {
    group.bullets.forEach((bullet, bulletIndex) => {
      if (
        bullet.bullet_text !==
        original.resume_bullets[groupIndex]?.bullets[bulletIndex]?.bullet_text
      ) {
        ids.add(resumeApplicationClaimId(groupIndex, bulletIndex));
      }
    });
  });
  if (editor.cover_letter.full_text !== original.cover_letter.full_text) {
    ids.add("cover-letter-full");
  }
  editor.application_snippets.forEach((snippet, index) => {
    const originalSnippet = snippet.question_id
      ? original.application_snippets.find(
          (candidate) => candidate.question_id === snippet.question_id,
        )
      : original.application_snippets[index];
    if (snippet.text !== originalSnippet?.text) {
      ids.add(snippetApplicationClaimId(index));
    }
  });
  return ids;
}

function versionHasUserReviewClaims(
  version: ApplicationPackageVersion,
): boolean {
  return version.claim_ledger.some(
    (claim) =>
      claim.user_edited || claim.support_level === "user_review_required",
  );
}

function targetFormFromPackageInput(input: ApplicationPackageInput): TargetForm {
  return {
    opportunityId: input.opportunityId ?? "",
    roleTitle: input.roleTitle,
    company: input.company ?? "",
    location: input.location ?? "",
    jobType: input.jobType ?? "",
    targetDescription: input.targetDescription,
    requiredSkills: input.requiredSkills.join("\n"),
    preferredSkills: input.preferredSkills.join("\n"),
    responsibilities: input.responsibilities.join("\n"),
    applicationQuestions: structuredClone(input.applicationQuestions),
  };
}

function packageInput(
  form: TargetForm,
  selectedMemoryIds: string[],
): ApplicationPackageInput {
  return {
    opportunityId: form.opportunityId || null,
    roleTitle: form.roleTitle,
    company: form.company || null,
    location: form.location || null,
    jobType: form.jobType || null,
    targetDescription: form.targetDescription,
    requiredSkills: splitPackageList(form.requiredSkills),
    preferredSkills: splitPackageList(form.preferredSkills),
    responsibilities: splitPackageList(form.responsibilities),
    applicationQuestions: structuredClone(form.applicationQuestions),
    selectedMemoryIds,
  };
}

function targetFromOpportunity(
  opportunity: ApplicationOpportunity,
  applicationQuestions: ApplicationQuestion[] = [],
): TargetForm {
  return {
    opportunityId: opportunity.id,
    roleTitle: applicationOpportunityRoleTitle(opportunity),
    company: opportunity.organization ?? "",
    location: "",
    jobType: "",
    targetDescription: opportunity.raw_text,
    requiredSkills: opportunity.detected_skills.join("\n"),
    preferredSkills: "",
    responsibilities: opportunity.detected_responsibilities.join("\n"),
    applicationQuestions: structuredClone(applicationQuestions),
  };
}

function newApplicationQuestion(): ApplicationQuestion {
  return {
    question_id: `question-${globalThis.crypto.randomUUID()}`,
    question_text: "",
    required: true,
    maximum_length: null,
    response_type: null,
    relevant_target_requirement_ids: [],
  };
}

function shortId(value: string): string {
  return value.length > 10 ? `${value.slice(0, 8)}…` : value;
}

function snapshotString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function dateTimeLabel(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? value
    : date.toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      });
}

function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "CareerOS could not complete that application package action.";
}
