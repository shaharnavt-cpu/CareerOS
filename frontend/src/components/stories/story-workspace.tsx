"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { WorkspaceNav } from "@/components/common/workspace-nav";
import {
  getDashboardSummary,
  type CanonicalReviewMemory,
} from "@/lib/knowledge-api";
import {
  discoverStories,
  listStories,
  mergeStories,
  renameStory,
  splitStory,
  transitionStory,
  type CareerStory,
  updateStory,
} from "@/lib/story-api";
import {
  activeStories,
  canSplitStory,
  coreExperiences,
  replaceStory,
} from "@/lib/story-utils";

const statusStyle: Record<CareerStory["status"], string> = {
  PROPOSED: "bg-[#fff1cf] text-[#82581c]",
  APPROVED: "bg-[#dff2e7] text-[#286247]",
  REJECTED: "bg-[#f8e8e3] text-[#915548]",
  ARCHIVED: "bg-[#e9ece9] text-[#65716c]",
};

export function StoryWorkspace() {
  const [stories, setStories] = useState<CareerStory[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [selectedStories, setSelectedStories] = useState<Set<string>>(
    new Set(),
  );
  const [selectedMemberships, setSelectedMemberships] = useState<Set<string>>(
    new Set(),
  );
  const [summary, setSummary] = useState("");
  const [approvedMemories, setApprovedMemories] = useState<
    CanonicalReviewMemory[]
  >([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(
    "Stories are suggestions until you approve them.",
  );

  const visibleStories = useMemo(() => activeStories(stories), [stories]);
  const active = stories.find((story) => story.id === activeId) ?? null;

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh(preferredId?: string) {
    setBusy(true);
    try {
      const [next, dashboard] = await Promise.all([
        listStories(),
        getDashboardSummary(),
      ]);
      setStories(next);
      setApprovedMemories(dashboard.recent_memories);
      const candidates = activeStories(next);
      const nextActiveId =
        preferredId && candidates.some((story) => story.id === preferredId)
          ? preferredId
          : (candidates[0]?.id ?? null);
      setActiveId(nextActiveId);
      setSummary(
        candidates.find((story) => story.id === nextActiveId)?.summary ?? "",
      );
      setSelectedMemberships(new Set());
    } catch (error) {
      setNotice(message(error));
    } finally {
      setBusy(false);
    }
  }

  async function discover() {
    setBusy(true);
    try {
      const result = await discoverStories();
      await refresh(result.stories[0]?.id);
      setNotice(
        result.stories.length
          ? `${result.stories.length} new story proposal${result.stories.length === 1 ? "" : "s"} found from ${result.experiences_considered} experiences.`
          : `No new groupings were needed across ${result.experiences_considered} experiences.`,
      );
    } catch (error) {
      setNotice(message(error));
      setBusy(false);
    }
  }

  async function saveSummary() {
    if (!active || !summary.trim()) return;
    await run(async () => {
      const updated = await updateStory(active.id, { summary: summary.trim() });
      setStories((current) => replaceStory(current, updated));
      setNotice(
        "Summary saved. The supporting Career Memory stayed unchanged.",
      );
    });
  }

  async function transition(action: "approve" | "reject" | "archive") {
    if (!active) return;
    await run(async () => {
      const updated = await transitionStory(active.id, action);
      setStories((current) => replaceStory(current, updated));
      if (action !== "approve") await refresh();
      setNotice(
        action === "approve"
          ? "Story approved by you and ready for future consumers."
          : `Story ${action === "reject" ? "rejected" : "archived"}.`,
      );
    });
  }

  async function rename() {
    if (!active) return;
    const title = window.prompt("Rename this story", active.title)?.trim();
    if (!title || title === active.title) return;
    await run(async () => {
      const updated = await renameStory(active.id, title);
      setStories((current) => replaceStory(current, updated));
      setNotice("Story renamed.");
    });
  }

  async function mergeSelected() {
    if (selectedStories.size < 2) return;
    const title = window.prompt("Title for the merged story")?.trim();
    if (!title) return;
    await run(async () => {
      const merged = await mergeStories([...selectedStories], title);
      setSelectedStories(new Set());
      await refresh(merged.id);
      setNotice(
        "Stories merged into a new proposal; source stories were archived.",
      );
    });
  }

  async function splitSelected() {
    if (!active || !canSplitStory(active, selectedMemberships)) return;
    const title = window.prompt("Title for the new story")?.trim();
    if (!title) return;
    await run(async () => {
      const created = await splitStory(
        active.id,
        [...selectedMemberships],
        title,
      );
      await refresh(created.id);
      setNotice(
        "Selected Career Memory items moved into a new story proposal.",
      );
    });
  }

  async function run(work: () => Promise<void>) {
    setBusy(true);
    try {
      await work();
    } catch (error) {
      setNotice(message(error));
    } finally {
      setBusy(false);
    }
  }

  function toggleStory(storyId: string) {
    setSelectedStories((current) => toggle(current, storyId));
  }

  function toggleMembership(membershipId: string) {
    setSelectedMemberships((current) => toggle(current, membershipId));
  }

  function chooseStory(story: CareerStory) {
    setActiveId(story.id);
    setSummary(story.summary);
    setSelectedMemberships(new Set());
  }

  return (
    <div className="min-h-screen bg-[#f3f5ef]">
      <WorkspaceNav active="stories" />

      <main className="mx-auto max-w-[1500px] px-5 py-8 sm:px-8 lg:py-10">
        <div className="flex flex-col justify-between gap-5 border-b border-[#d7dfda] pb-7 lg:flex-row lg:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#438065]">
              Career Story Intelligence
            </p>
            <h1 className="mt-2 text-4xl font-semibold tracking-[-0.045em] text-[#15362c] sm:text-5xl">
              Find the thread, not just the timeline.
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-[#687a72]">
              Review how your experiences connect, inspect every reason and
              source, then shape the narratives that feel true to you.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className="min-h-11 rounded-full border border-[#cbd8d1] px-5 text-sm font-semibold text-[#365e4f] transition hover:bg-white disabled:opacity-50"
              disabled={busy}
              onClick={() => void refresh(activeId ?? undefined)}
              type="button"
            >
              Refresh workspace
            </button>
            <button
              className="min-h-11 rounded-full bg-[#173f35] px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#245849] disabled:opacity-50"
              disabled={busy}
              onClick={() => void discover()}
              type="button"
            >
              {busy ? "Working…" : "Discover stories"}
            </button>
          </div>
        </div>

        <div
          className="mt-5 rounded-2xl border border-[#cfe0d6] bg-[#eaf5ee] px-4 py-3 text-sm text-[#3c6655]"
          aria-live="polite"
        >
          {notice}
        </div>

        {visibleStories.length === 0 ? (
          <section className="mt-7 rounded-[28px] border border-dashed border-[#c9d5ce] bg-white p-10 text-center">
            <p className="text-xl font-semibold text-[#27483d]">
              Stories will be built from your approved memories.
            </p>
            <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-[#708079]">
              CareerOS can look for goals, organizations, skills, chronology,
              and recurring themes once enough approved Career Memory is
              available.
            </p>
            {approvedMemories.length > 0 ? (
              <div className="mx-auto mt-6 grid max-w-3xl gap-3 text-left md:grid-cols-2">
                {approvedMemories.map((memory) => (
                  <article
                    className="rounded-2xl border border-[#dfe7e2] bg-[#fbfcfa] p-4"
                    key={memory.id}
                  >
                    <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#6f8279]">
                      {memory.memory_type.replaceAll("_", " ")}
                    </p>
                    <h2 className="mt-1 text-sm font-semibold text-[#29483e]">
                      {memory.title}
                    </h2>
                    <p className="mt-2 text-xs leading-5 text-[#71817b]">
                      {memory.evidence_ids.length} evidence reference
                      {memory.evidence_ids.length === 1 ? "" : "s"} attached
                    </p>
                  </article>
                ))}
              </div>
            ) : (
              <p className="mx-auto mt-4 max-w-lg text-xs leading-5 text-[#81908a]">
                Approve a few memories in review first; they will show up here
                as story ingredients.
              </p>
            )}
            <div className="mt-6 flex justify-center gap-3">
              <Link
                className="rounded-full border border-[#cbd8d1] px-4 py-2 text-sm font-semibold text-[#365e4f]"
                href="/review"
              >
                Review memories
              </Link>
              <button
                className="rounded-full bg-[#173f35] px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                disabled={busy || approvedMemories.length === 0}
                onClick={() => void discover()}
                type="button"
              >
                Discover stories
              </button>
            </div>
          </section>
        ) : (
          <div className="mt-7 grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
            <aside className="rounded-[26px] border border-[#d8e0db] bg-white p-4 shadow-[0_18px_50px_-42px_rgba(22,54,44,0.7)]">
              <div className="flex items-center justify-between px-2 pb-3">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#74857e]">
                    Story map
                  </p>
                  <p className="mt-1 text-sm text-[#6c7d76]">
                    {visibleStories.length} active narratives
                  </p>
                </div>
                <button
                  className="rounded-full border border-[#cbd8d1] px-3 py-1.5 text-xs font-semibold text-[#365e4f] disabled:opacity-40"
                  disabled={selectedStories.size < 2 || busy}
                  onClick={() => void mergeSelected()}
                  type="button"
                >
                  Merge {selectedStories.size || ""}
                </button>
              </div>
              <div className="space-y-2">
                {visibleStories.map((story) => (
                  <div
                    className={`rounded-2xl border p-3 transition ${story.id === activeId ? "border-[#8fbba6] bg-[#edf6f0]" : "border-[#e1e7e3] hover:bg-[#f7f9f6]"}`}
                    key={story.id}
                  >
                    <div className="flex gap-3">
                      <input
                        aria-label={`Select ${story.title} for merge`}
                        checked={selectedStories.has(story.id)}
                        className="mt-1 h-4 w-4 accent-[#29644f]"
                        onChange={() => toggleStory(story.id)}
                        type="checkbox"
                      />
                      <button
                        className="min-w-0 flex-1 text-left"
                        onClick={() => chooseStory(story)}
                        type="button"
                      >
                        <span className="block truncate text-sm font-semibold text-[#234238]">
                          {story.title}
                        </span>
                        <span className="mt-1.5 flex items-center gap-2 text-[11px] text-[#71817b]">
                          <span
                            className={`rounded-full px-2 py-0.5 font-bold ${statusStyle[story.status]}`}
                          >
                            {story.status}
                          </span>
                          {coreExperiences(story).length} experiences
                        </span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </aside>

            {active && (
              <section className="rounded-[28px] border border-[#d8e0db] bg-white p-5 shadow-[0_18px_50px_-42px_rgba(22,54,44,0.7)] sm:p-7">
                <div className="flex flex-col justify-between gap-4 border-b border-[#e4e9e6] pb-6 sm:flex-row sm:items-start">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`rounded-full px-2.5 py-1 text-[10px] font-bold tracking-[0.08em] ${statusStyle[active.status]}`}
                      >
                        {active.status}
                      </span>
                      <span className="text-xs text-[#778880]">
                        {Math.round(active.confidence * 100)}% confidence
                      </span>
                    </div>
                    <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-[#183a30]">
                      {active.title}
                    </h2>
                    <p className="mt-2 text-xs text-[#82908b]">
                      Proposed by CareerOS · approved only by you
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      className="rounded-full border border-[#d5dfd9] px-3.5 py-2 text-xs font-semibold text-[#50675e]"
                      onClick={() => void rename()}
                      type="button"
                    >
                      Rename
                    </button>
                    {active.status === "PROPOSED" && (
                      <>
                        <button
                          className="rounded-full bg-[#dff1e7] px-3.5 py-2 text-xs font-semibold text-[#286148]"
                          disabled={busy}
                          onClick={() => void transition("approve")}
                          type="button"
                        >
                          Approve
                        </button>
                        <button
                          className="rounded-full px-3.5 py-2 text-xs font-semibold text-[#95594c]"
                          disabled={busy}
                          onClick={() => void transition("reject")}
                          type="button"
                        >
                          Reject
                        </button>
                      </>
                    )}
                    <button
                      className="rounded-full px-3.5 py-2 text-xs font-semibold text-[#6c7672]"
                      disabled={busy}
                      onClick={() => void transition("archive")}
                      type="button"
                    >
                      Archive
                    </button>
                  </div>
                </div>

                <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1fr)_280px]">
                  <div className="space-y-5">
                    <div>
                      <label
                        className="text-xs font-bold uppercase tracking-[0.12em] text-[#60746b]"
                        htmlFor="story-summary"
                      >
                        Narrative summary
                      </label>
                      <textarea
                        className="mt-2 min-h-32 w-full resize-y rounded-2xl border border-[#cfdbd4] bg-[#fbfcfa] p-4 text-sm leading-6 text-[#344e44] outline-none ring-[#dceee5] focus:ring-4"
                        id="story-summary"
                        onChange={(event) => setSummary(event.target.value)}
                        value={summary}
                      />
                      <button
                        className="mt-2 rounded-full bg-[#214f40] px-4 py-2 text-xs font-semibold text-white disabled:opacity-40"
                        disabled={
                          busy || !summary.trim() || summary === active.summary
                        }
                        onClick={() => void saveSummary()}
                        type="button"
                      >
                        Save summary
                      </button>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <NarrativeField
                        label="Primary goal"
                        value={active.primary_goal}
                      />
                      <NarrativeField
                        label="Transformation"
                        value={active.transformation}
                      />
                    </div>

                    <div>
                      <div className="flex items-end justify-between gap-3">
                        <div>
                          <h3 className="text-sm font-bold uppercase tracking-[0.12em] text-[#50675e]">
                            Included Career Memory
                          </h3>
                          <p className="mt-1 text-xs text-[#84918c]">
                            Select some—but not all—to split into a new story.
                          </p>
                        </div>
                        <button
                          className="rounded-full border border-[#cbd9d2] px-3 py-1.5 text-xs font-semibold text-[#345e4e] disabled:opacity-40"
                          disabled={
                            !canSplitStory(active, selectedMemberships) || busy
                          }
                          onClick={() => void splitSelected()}
                          type="button"
                        >
                          Split selected
                        </button>
                      </div>
                      <div className="mt-3 space-y-2">
                        {active.memberships.map((membership) => (
                          <label
                            className="flex cursor-pointer gap-3 rounded-2xl border border-[#e0e6e2] p-3.5 hover:bg-[#f8faf7]"
                            key={membership.id}
                          >
                            <input
                              checked={selectedMemberships.has(membership.id)}
                              className="mt-1 h-4 w-4 accent-[#29644f]"
                              onChange={() => toggleMembership(membership.id)}
                              type="checkbox"
                            />
                            <span className="min-w-0">
                              <span className="flex flex-wrap items-center gap-2">
                                <span className="font-semibold text-[#29473d]">
                                  {membership.label}
                                </span>
                                <span className="rounded-full bg-[#edf2ee] px-2 py-0.5 text-[9px] font-bold text-[#63756d]">
                                  {membership.entity_type}
                                </span>
                              </span>
                              {membership.organization && (
                                <span className="mt-0.5 block text-xs text-[#71817b]">
                                  {membership.organization}
                                </span>
                              )}
                              <span className="mt-1.5 block text-xs leading-5 text-[#64766f]">
                                Why it fits: {membership.rationale}
                              </span>
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>

                  <aside className="space-y-4">
                    <div className="rounded-2xl bg-[#f3f6f2] p-4">
                      <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-[#60746b]">
                        Chapters
                      </h3>
                      <ol className="mt-3 space-y-3">
                        {active.chapters.map((chapter, index) => (
                          <li
                            className="flex gap-2.5 text-sm text-[#435b52]"
                            key={chapter.id}
                          >
                            <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-white text-[10px] font-bold text-[#42715d]">
                              {index + 1}
                            </span>
                            <span>{chapter.title}</span>
                          </li>
                        ))}
                      </ol>
                    </div>
                    <div className="rounded-2xl border border-[#dde5e0] p-4">
                      <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-[#60746b]">
                        Supporting evidence
                      </h3>
                      {active.evidence.length ? (
                        <div className="mt-3 space-y-3">
                          {active.evidence.map((evidence) => (
                            <article
                              className="border-b border-[#e8ece9] pb-3 last:border-0 last:pb-0"
                              key={evidence.id}
                            >
                              <p className="text-sm font-semibold text-[#335247]">
                                {evidence.title}
                              </p>
                              <p className="mt-1 text-[10px] font-bold text-[#6e8179]">
                                {evidence.verification_status.replaceAll(
                                  "_",
                                  " ",
                                )}
                              </p>
                              {evidence.excerpt && (
                                <p className="mt-1.5 text-xs leading-5 text-[#65776f]">
                                  “{evidence.excerpt}”
                                </p>
                              )}
                              {evidence.source_url && (
                                <a
                                  className="mt-1.5 inline-block text-xs font-semibold text-[#34745b] underline"
                                  href={evidence.source_url}
                                  rel="noreferrer"
                                  target="_blank"
                                >
                                  Open source
                                </a>
                              )}
                            </article>
                          ))}
                        </div>
                      ) : (
                        <p className="mt-3 text-xs leading-5 text-[#7b8a84]">
                          No canonical evidence is linked yet. The membership
                          reasons remain visible for review.
                        </p>
                      )}
                    </div>
                  </aside>
                </div>
              </section>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

function NarrativeField({
  label,
  value,
}: {
  label: string;
  value: string | null;
}) {
  return (
    <div className="rounded-2xl bg-[#f5f7f3] p-4">
      <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#71817b]">
        {label}
      </p>
      <p className="mt-2 text-sm leading-6 text-[#40574e]">
        {cleanStoryText(value)}
      </p>
    </div>
  );
}

function cleanStoryText(value: string | null): string {
  const cleaned = value?.trim();
  if (!cleaned) return "Not enough evidence yet.";
  if (/^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)$/i.test(cleaned)) {
    return "Not enough evidence yet.";
  }
  if (cleaned.length < 4) return "Not enough evidence yet.";
  return cleaned;
}

function toggle(values: Set<string>, value: string): Set<string> {
  const next = new Set(values);
  if (next.has(value)) next.delete(value);
  else next.add(value);
  return next;
}

function message(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "CareerOS could not complete that story action.";
}
