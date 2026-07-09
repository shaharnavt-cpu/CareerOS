"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { Brand } from "@/components/common/brand";
import {
  createApplicationOpportunity,
  draftApplicationOpportunity,
  draftApplicationQuestion,
  updateApplicationDraft,
  type ApplicationDraft,
  type ApplicationMemoryMatch,
  type ApplicationOpportunity,
} from "@/lib/application-api";
import {
  applicationMatchSummary,
  applicationMemoryTypeLabel,
  draftStatusLabel,
  evidenceCountLabel,
} from "@/lib/application-utils";

const sampleOpportunity = `Data Analytics Intern

We are looking for a student intern to support data analysis, reporting, and business insight generation. Responsibilities include cleaning data, using Python or SQL to analyze datasets, creating summaries or visuals, and communicating findings to non-technical stakeholders. Preferred qualifications include experience with Excel, Python, SQL, analytics coursework, and project experience translating data into recommendations.

Application question:
Tell us about a project or experience that prepared you for this analytics internship.`;

export function ApplicationWorkspace() {
  const [input, setInput] = useState(sampleOpportunity);
  const [opportunity, setOpportunity] = useState<ApplicationOpportunity | null>(
    null,
  );
  const [drafts, setDrafts] = useState<ApplicationDraft[]>([]);
  const [busy, setBusy] = useState(false);
  const [draftingId, setDraftingId] = useState<string | null>(null);
  const [notice, setNotice] = useState(
    "Paste a role, posting, or question. Drafts only use approved Career Memory.",
  );

  const generalMatches = useMemo(
    () => opportunity?.matches.filter((match) => match.question_id == null) ?? [],
    [opportunity],
  );
  const visibleDrafts = useMemo(
    () => [...drafts, ...(opportunity?.drafts ?? [])],
    [drafts, opportunity],
  );

  async function analyze() {
    const rawText = input.trim();
    if (!rawText) {
      setNotice("Paste an opportunity or application question first.");
      return;
    }
    setBusy(true);
    try {
      const created = await createApplicationOpportunity({ raw_text: rawText });
      setOpportunity(created);
      setDrafts([]);
      setNotice(
        created.matches.length
          ? applicationMatchSummary(created.matches, created.gaps)
          : "Opportunity analyzed. Approve Career Memory to improve matching.",
      );
    } catch (error) {
      setNotice(message(error));
    } finally {
      setBusy(false);
    }
  }

  async function draftGeneral() {
    if (!opportunity) return;
    setDraftingId("general");
    try {
      const result = await draftApplicationOpportunity(opportunity.id, {
        draft_type: "GENERAL_RESPONSE",
        length: "MEDIUM",
      });
      setDrafts((current) => [result.draft, ...current]);
      setNotice("Evidence-backed draft generated from approved memories.");
    } catch (error) {
      setNotice(message(error));
    } finally {
      setDraftingId(null);
    }
  }

  async function draftQuestion(questionId: string) {
    setDraftingId(questionId);
    try {
      const result = await draftApplicationQuestion(questionId, {
        draft_type: "QUESTION_ANSWER",
        length: "MEDIUM",
      });
      setDrafts((current) => [result.draft, ...current]);
      setNotice("Question draft generated. You can edit and save it.");
    } catch (error) {
      setNotice(message(error));
    } finally {
      setDraftingId(null);
    }
  }

  async function saveDraft(draft: ApplicationDraft, draftText: string) {
    try {
      const saved = await updateApplicationDraft(draft.id, {
        draft_text: draftText,
        status: "APPROVED",
      });
      setDrafts((current) =>
        current.map((item) => (item.id === saved.id ? saved : item)),
      );
      setOpportunity((current) =>
        current
          ? {
              ...current,
              drafts: current.drafts.map((item) =>
                item.id === saved.id ? saved : item,
              ),
            }
          : current,
      );
      setNotice("Draft saved. The underlying Career Memory stayed unchanged.");
    } catch (error) {
      setNotice(message(error));
    }
  }

  return (
    <div className="min-h-screen bg-[#f4f6f0]">
      <header className="border-b border-[#d9e1db] bg-[#fbfcf8]/95 px-5 py-4 backdrop-blur-xl sm:px-8">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <Brand />
          <nav className="flex items-center gap-2 text-sm font-semibold text-[#52665e]">
            <Link className="rounded-full px-4 py-2 hover:bg-[#edf3ee]" href="/dashboard">
              Career Memory
            </Link>
            <span className="rounded-full bg-[#173f35] px-4 py-2 text-white">
              Applications
            </span>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-5 py-9 sm:px-8 lg:py-12">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
          <section className="rounded-[28px] border border-[#dce4df] bg-white p-5 shadow-[0_18px_45px_-38px_rgba(23,63,53,0.8)] sm:p-6">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#3f8064]">
              Application Intelligence
            </p>
            <h1 className="mt-3 text-4xl font-semibold tracking-[-0.045em] text-[#142f26]">
              Match a role to approved memory.
            </h1>
            <p className="mt-3 text-sm leading-6 text-[#6d7e77]">
              CareerOS reads the posting, finds relevant approved memories, and
              drafts answers without using rejected or unapproved claims.
            </p>

            <label
              className="mt-6 block text-xs font-bold uppercase tracking-[0.12em] text-[#61766d]"
              htmlFor="application-input"
            >
              Job description or application question
            </label>
            <textarea
              className="mt-2 min-h-80 w-full resize-y rounded-2xl border border-[#cfdbd4] bg-[#fbfcfa] p-4 text-sm leading-6 text-[#344e44] outline-none ring-[#dceee5] focus:ring-4"
              id="application-input"
              onChange={(event) => setInput(event.target.value)}
              value={input}
            />
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                className="rounded-full bg-[#173f35] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#285b4a] disabled:opacity-50"
                disabled={busy}
                onClick={() => void analyze()}
                type="button"
              >
                {busy ? "Analyzing..." : "Analyze opportunity"}
              </button>
              <button
                className="rounded-full border border-[#c7d8cf] px-5 py-2.5 text-sm font-semibold text-[#35634f]"
                onClick={() => setInput(sampleOpportunity)}
                type="button"
              >
                Load sample
              </button>
            </div>
            <div
              aria-live="polite"
              className="mt-5 rounded-2xl border border-[#cfe0d6] bg-[#eaf5ee] px-4 py-3 text-sm text-[#3c6655]"
            >
              {notice}
            </div>
          </section>

          <section className="space-y-5">
            {opportunity ? (
              <>
                <OpportunitySummary opportunity={opportunity} />
                <MatchPanel
                  gaps={opportunity.gaps}
                  matches={generalMatches}
                  onDraft={() => void draftGeneral()}
                  drafting={draftingId === "general"}
                />
                {opportunity.questions.length > 0 && (
                  <QuestionPanel
                    draftingId={draftingId}
                    onDraft={draftQuestion}
                    opportunity={opportunity}
                  />
                )}
                <DraftPanel drafts={visibleDrafts} onSave={saveDraft} />
              </>
            ) : (
              <div className="rounded-[28px] border border-dashed border-[#cdd8d1] bg-white p-8 text-center">
                <p className="text-lg font-semibold text-[#2d4b40]">
                  Waiting for an opportunity.
                </p>
                <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-[#708079]">
                  Once analyzed, this area will show detected skills, ranked
                  approved memories, evidence gaps, and draft answers.
                </p>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}

function OpportunitySummary({
  opportunity,
}: {
  opportunity: ApplicationOpportunity;
}) {
  return (
    <section className="rounded-[26px] border border-[#dce4df] bg-white p-5">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7d8e87]">
        Opportunity understanding
      </p>
      <h2 className="mt-1 text-2xl font-semibold text-[#17362d]">
        {opportunity.title}
      </h2>
      <p className="mt-2 text-sm text-[#6f8079]">
        {opportunity.organization
          ? `${opportunity.organization} · `
          : ""}
        {opportunity.detected_role_type ?? "Role type unknown"}
      </p>
      <TagRow items={opportunity.detected_skills} label="Detected skills" />
      <TagRow items={opportunity.detected_keywords} label="Themes" />
      {opportunity.detected_responsibilities.length > 0 && (
        <div className="mt-4">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#6a7c74]">
            Responsibilities
          </p>
          <ul className="mt-2 space-y-1.5 text-sm leading-6 text-[#5f726a]">
            {opportunity.detected_responsibilities.slice(0, 4).map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function MatchPanel({
  matches,
  gaps,
  onDraft,
  drafting,
}: {
  matches: ApplicationMemoryMatch[];
  gaps: string[];
  onDraft: () => void;
  drafting: boolean;
}) {
  return (
    <section className="rounded-[26px] border border-[#dce4df] bg-white p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7d8e87]">
            Matched from approved memory
          </p>
          <h2 className="mt-1 text-xl font-semibold text-[#17362d]">
            {matches.length} relevant memories
          </h2>
        </div>
        <button
          className="rounded-full bg-[#e4f3ea] px-4 py-2 text-xs font-semibold text-[#2c684f] disabled:opacity-50"
          disabled={!matches.length || drafting}
          onClick={onDraft}
          type="button"
        >
          {drafting ? "Drafting..." : "Draft answer"}
        </button>
      </div>
      <div className="mt-4 space-y-3">
        {matches.map((match) => (
          <MemoryMatchCard match={match} key={match.id} />
        ))}
      </div>
      {gaps.length > 0 && (
        <div className="mt-4 rounded-2xl border border-[#ead6a9] bg-[#fff8e8] p-4 text-sm text-[#76541f]">
          <p className="font-semibold">Missing evidence</p>
          <p className="mt-1">
            {gaps.join(", ")} has not been approved in Career Memory yet.
          </p>
        </div>
      )}
    </section>
  );
}

function QuestionPanel({
  opportunity,
  draftingId,
  onDraft,
}: {
  opportunity: ApplicationOpportunity;
  draftingId: string | null;
  onDraft: (questionId: string) => Promise<void>;
}) {
  return (
    <section className="rounded-[26px] border border-[#dce4df] bg-white p-5">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7d8e87]">
        Application questions
      </p>
      <div className="mt-3 space-y-3">
        {opportunity.questions.map((question) => (
          <article
            className="rounded-2xl border border-[#e3e9e5] bg-[#fbfcfa] p-4"
            key={question.id}
          >
            <p className="text-sm font-semibold text-[#29483e]">
              {question.question_text}
            </p>
            <p className="mt-1 text-xs text-[#6f8079]">
              {question.question_type.replaceAll("_", " ")} ·{" "}
              {question.detected_intent}
            </p>
            <button
              className="mt-3 rounded-full bg-[#173f35] px-4 py-2 text-xs font-semibold text-white disabled:opacity-50"
              disabled={draftingId === question.id}
              onClick={() => void onDraft(question.id)}
              type="button"
            >
              {draftingId === question.id ? "Drafting..." : "Draft response"}
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}

function DraftPanel({
  drafts,
  onSave,
}: {
  drafts: ApplicationDraft[];
  onSave: (draft: ApplicationDraft, draftText: string) => Promise<void>;
}) {
  if (!drafts.length) return null;
  return (
    <section className="rounded-[26px] border border-[#dce4df] bg-white p-5">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7d8e87]">
        Evidence-backed drafts
      </p>
      <div className="mt-4 space-y-4">
        {drafts.map((draft) => (
          <DraftCard draft={draft} key={draft.id} onSave={onSave} />
        ))}
      </div>
    </section>
  );
}

function DraftCard({
  draft,
  onSave,
}: {
  draft: ApplicationDraft;
  onSave: (draft: ApplicationDraft, draftText: string) => Promise<void>;
}) {
  const [value, setValue] = useState(draft.draft_text);
  return (
    <article className="rounded-2xl border border-[#dfe7e2] bg-[#fbfcfa] p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#60746b]">
          {draft.draft_type.replaceAll("_", " ")}
        </p>
        <span className="rounded-full bg-[#edf3ef] px-2.5 py-1 text-[10px] font-bold text-[#60746b]">
          {draftStatusLabel(draft.status)}
        </span>
      </div>
      <textarea
        className="mt-3 min-h-44 w-full resize-y rounded-2xl border border-[#cfdbd4] bg-white p-4 text-sm leading-6 text-[#344e44] outline-none ring-[#dceee5] focus:ring-4"
        onChange={(event) => setValue(event.target.value)}
        value={value}
      />
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-[#71817b]">
          Evidence used: {evidenceCountLabel(draft.evidence_ids.length)}
        </p>
        <button
          className="rounded-full bg-[#214f40] px-4 py-2 text-xs font-semibold text-white"
          onClick={() => void onSave(draft, value)}
          type="button"
        >
          Save draft
        </button>
      </div>
    </article>
  );
}

function MemoryMatchCard({ match }: { match: ApplicationMemoryMatch }) {
  return (
    <article className="rounded-2xl border border-[#e3e9e5] bg-[#fbfcfa] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[#29483e]">
            {match.memory.title}
          </p>
          <p className="mt-1 text-xs font-bold uppercase tracking-[0.1em] text-[#4d7967]">
            {applicationMemoryTypeLabel(match.memory.memory_type)}
          </p>
        </div>
        <span className="rounded-full bg-[#e4f3ea] px-2.5 py-1 text-[10px] font-bold text-[#2f6d53]">
          {Math.round(match.match_score * 100)}%
        </span>
      </div>
      <p className="mt-2 text-sm leading-6 text-[#61736b]">{match.match_reason}</p>
      <p className="mt-2 text-xs text-[#7b8a84]">
        {evidenceCountLabel(match.evidence_ids.length)} · themes:{" "}
        {match.themes_matched.join(", ")}
      </p>
    </article>
  );
}

function TagRow({ items, label }: { items: string[]; label: string }) {
  if (!items.length) return null;
  return (
    <div className="mt-4">
      <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#6a7c74]">
        {label}
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        {items.map((item) => (
          <span
            className="rounded-full bg-[#edf4f0] px-3 py-1 text-xs font-semibold text-[#426657]"
            key={item}
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

function message(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "CareerOS could not complete that application action.";
}
