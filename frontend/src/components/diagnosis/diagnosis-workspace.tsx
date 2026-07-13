"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { WorkspaceNav } from "@/components/common/workspace-nav";
import {
  createDiagnosisSession,
  createFeedbackEvent,
  listDiagnosisSessions,
  listFeedbackEvents,
  rerunDiagnosisSession,
  updateFeedbackEvent,
  DiagnosisApiError,
  type CareerFeedbackEvent,
  type DiagnosisFocus,
  type DiagnosisResult,
  type DiagnosisSession,
  type FeedbackEventStatus,
} from "@/lib/diagnosis-api";
import {
  diagnosisConfidenceLabel,
  diagnosisFocusLabel,
  evidenceStrengthLabel,
  feedbackEventTypeLabel,
  feedbackStatusLabel,
} from "@/lib/diagnosis-utils";

const focusOptions: DiagnosisFocus[] = [
  "ANALYTICS",
  "AI_AUTOMATION",
  "RESEARCH",
  "QUANT_FINANCE",
  "CAMPUS_JOB",
  "SCHOLARSHIP_LEADERSHIP",
  "GENERAL",
];

export function DiagnosisWorkspace() {
  const [targetRole, setTargetRole] = useState("");
  const [context, setContext] = useState("");
  const [focus, setFocus] = useState<DiagnosisFocus>("GENERAL");
  const [diagnosis, setDiagnosis] = useState<DiagnosisSession | null>(null);
  const [feedbackEvents, setFeedbackEvents] = useState<CareerFeedbackEvent[]>([]);
  const [feedbackNote, setFeedbackNote] = useState("");
  const [running, setRunning] = useState(false);
  const [teaching, setTeaching] = useState(false);
  const [notice, setNotice] = useState(
    "CareerOS is loading your latest diagnosis and feedback events.",
  );

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([listDiagnosisSessions(), listFeedbackEvents()]).then(
      ([sessionsResult, feedbackResult]) => {
        if (cancelled) return;
        if (sessionsResult.status === "fulfilled" && sessionsResult.value.length) {
          const latest = sessionsResult.value[0];
          setDiagnosis(latest);
          setTargetRole(latest.target_role ?? "");
          setContext(latest.frustration_context ?? "");
          setFocus(latest.selected_focus ?? "GENERAL");
        }
        if (feedbackResult.status === "fulfilled") {
          setFeedbackEvents(feedbackResult.value);
        }
        if (
          sessionsResult.status === "rejected" &&
          feedbackResult.status === "rejected"
        ) {
          setNotice(
            "CareerOS could not load the diagnosis workspace. Check the backend and retry.",
          );
        } else if (
          sessionsResult.status === "fulfilled" &&
          sessionsResult.value.length
        ) {
          setNotice("Loaded your latest saved Career Diagnosis.");
        } else {
          setNotice(
            "Choose a target or run a general diagnosis from approved Career Memory.",
          );
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);

  async function runDiagnosis() {
    setRunning(true);
    setNotice("Comparing your target with approved Career Memory…");
    try {
      const created = await createDiagnosisSession({
        target_role: targetRole.trim() || undefined,
        frustration_context: context.trim() || undefined,
        selected_focus: focus,
      });
      setDiagnosis(created);
      setNotice(
        created.status === "NEEDS_MEMORY"
          ? "Approve career memories before running a full diagnosis."
          : "Diagnosis complete. Evidence and inference are labeled separately.",
      );
    } catch (error) {
      setNotice(errorMessage(error));
    } finally {
      setRunning(false);
    }
  }

  async function rerun() {
    if (!diagnosis) return;
    setRunning(true);
    setNotice("Recomputing this diagnosis from current approved memory…");
    try {
      const updated = await rerunDiagnosisSession(diagnosis.id);
      setDiagnosis(updated);
      setNotice("Diagnosis rerun completed from current approved memory.");
    } catch (error) {
      setNotice(errorMessage(error));
    } finally {
      setRunning(false);
    }
  }

  async function teachCareerOS() {
    const note = feedbackNote.trim();
    if (!note) {
      setNotice("Tell CareerOS what happened or how a memory should be framed.");
      return;
    }
    setTeaching(true);
    try {
      const event = await createFeedbackEvent({ raw_note: note });
      setFeedbackEvents((current) => [event, ...current]);
      setFeedbackNote("");
      setNotice(
        "Feedback saved as a proposed learning event. Review it before CareerOS uses it.",
      );
    } catch (error) {
      setNotice(
        error instanceof DiagnosisApiError &&
          error.code === "DUPLICATE_FEEDBACK_EVENT"
          ? "This looks similar to an existing feedback event."
          : errorMessage(error),
      );
    } finally {
      setTeaching(false);
    }
  }

  async function changeFeedbackStatus(
    event: CareerFeedbackEvent,
    status: FeedbackEventStatus,
  ) {
    try {
      const updated = await updateFeedbackEvent(event.id, { status });
      setFeedbackEvents((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setNotice(
        status === "APPROVED"
          ? "Feedback approved as user guidance, not canonical factual proof."
          : "Feedback event archived.",
      );
    } catch (error) {
      setNotice(errorMessage(error));
    }
  }

  async function editFeedbackEvent(
    event: CareerFeedbackEvent,
    rawNote: string,
  ): Promise<boolean> {
    const correctedNote = rawNote.trim();
    if (!correctedNote) {
      setNotice("A feedback event needs a note before it can be saved.");
      return false;
    }
    try {
      const updated = await updateFeedbackEvent(event.id, {
        raw_note: correctedNote,
      });
      setFeedbackEvents((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setNotice(
        "Feedback event corrected and reparsed. Its review status was preserved.",
      );
      return true;
    } catch (error) {
      setNotice(errorMessage(error));
      return false;
    }
  }

  return (
    <div className="min-h-screen bg-[#f6f7f2]">
      <WorkspaceNav active="diagnosis" />
      <main className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:py-14">
        <section className="grid gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#3f8064]">
              Career judgment workspace
            </p>
            <h1 className="mt-3 max-w-3xl text-4xl font-semibold tracking-[-0.045em] text-[#142f26] sm:text-5xl">
              Career Diagnosis
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-[#63766e]">
              See the identity your approved memory supports, the proof an evaluator
              may miss, and the one artifact worth building this week.
            </p>
          </div>
          <div className="rounded-[24px] border border-[#cfe0d6] bg-[#eaf5ee] p-5">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#3f8064]">
              Trust boundary
            </p>
            <p className="mt-2 text-sm leading-6 text-[#45665a]">
              Trusted claims use approved canonical Career Memory only. Target text,
              frustration, and Teach CareerOS notes can guide judgment, but they are
              not treated as factual proof.
            </p>
          </div>
        </section>

        <section className="mt-8 rounded-[28px] border border-[#dce4df] bg-white p-5 sm:p-7">
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7d8e87]">
                Diagnosis input
              </p>
              <h2 className="mt-1 text-2xl font-semibold text-[#17362d]">
                What should CareerOS evaluate?
              </h2>
            </div>
            {diagnosis && (
              <button
                className="rounded-full border border-[#c7d8cf] px-4 py-2 text-xs font-semibold text-[#35634f] disabled:opacity-50"
                disabled={running}
                onClick={() => void rerun()}
                type="button"
              >
                Rerun saved diagnosis
              </button>
            )}
          </div>
          <div className="mt-6 grid gap-5 lg:grid-cols-2">
            <label className="text-sm font-semibold text-[#365247]">
              Target role or program
              <input
                className="mt-2 min-h-12 w-full rounded-2xl border border-[#cfdbd4] bg-[#fbfcfa] px-4 font-normal text-[#29483e] outline-none ring-[#dceee5] placeholder:text-[#96a39d] focus:ring-4"
                onChange={(event) => setTargetRole(event.target.value)}
                placeholder="Data Analytics / AI internship"
                value={targetRole}
              />
            </label>
            <label className="text-sm font-semibold text-[#365247]">
              Selected focus
              <select
                className="mt-2 min-h-12 w-full rounded-2xl border border-[#cfdbd4] bg-[#fbfcfa] px-4 font-normal text-[#29483e] outline-none ring-[#dceee5] focus:ring-4"
                onChange={(event) => setFocus(event.target.value as DiagnosisFocus)}
                value={focus}
              >
                {focusOptions.map((option) => (
                  <option key={option} value={option}>
                    {diagnosisFocusLabel(option)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="mt-5 block text-sm font-semibold text-[#365247]">
            Optional context or frustration
            <textarea
              className="mt-2 min-h-32 w-full resize-y rounded-2xl border border-[#cfdbd4] bg-[#fbfcfa] p-4 font-normal leading-6 text-[#29483e] outline-none ring-[#dceee5] placeholder:text-[#96a39d] focus:ring-4"
              onChange={(event) => setContext(event.target.value)}
              placeholder="I feel like my background is scattered and I am not sure what employers will recognize."
              value={context}
            />
          </label>
          <div className="mt-5 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <p className="text-xs leading-5 text-[#75857e]">
              Leave the target blank for a general diagnosis of your current Career
              Memory.
            </p>
            <button
              className="min-h-12 rounded-full bg-[#173f35] px-6 text-sm font-semibold text-white transition hover:bg-[#285b4a] disabled:cursor-not-allowed disabled:opacity-60"
              disabled={running}
              onClick={() => void runDiagnosis()}
              type="button"
            >
              {running ? "Running diagnosis…" : "Run diagnosis"}
            </button>
          </div>
        </section>

        <div
          aria-live="polite"
          className="mt-5 rounded-2xl border border-[#d9e4de] bg-[#fbfcfa] px-4 py-3 text-sm text-[#587066]"
        >
          {notice}
        </div>

        {!diagnosis && <DiagnosisStartState />}
        {diagnosis?.status === "NEEDS_MEMORY" && (
          <EmptyMemoryDiagnosis result={diagnosis.result} />
        )}
        {diagnosis?.status === "COMPLETE" && (
          <DiagnosisBrief result={diagnosis.result} />
        )}

        <TeachCareerOSPanel
          events={feedbackEvents}
          note={feedbackNote}
          onChangeNote={setFeedbackNote}
          onChangeStatus={changeFeedbackStatus}
          onEdit={editFeedbackEvent}
          onTeach={teachCareerOS}
          teaching={teaching}
        />
      </main>
    </div>
  );
}

function DiagnosisStartState() {
  return (
    <section className="mt-5 rounded-[26px] border border-dashed border-[#c9d8d0] bg-[#fbfcfa] p-8 text-center">
      <p className="text-sm font-semibold text-[#315447]">No diagnosis selected yet</p>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-[#73847d]">
        Run a general diagnosis or name a target. CareerOS will show where the
        conclusion is evidence and where it is inference.
      </p>
    </section>
  );
}

function EmptyMemoryDiagnosis({ result }: { result: DiagnosisResult }) {
  return (
    <section className="mt-5 rounded-[28px] border border-[#e0d3b8] bg-[#fff9ec] p-6 sm:p-8">
      <p className="text-xs font-bold uppercase tracking-[0.15em] text-[#8b672e]">
        Approved memory needed
      </p>
      <h2 className="mt-2 text-2xl font-semibold text-[#513f23]">
        {result.career_identity}
      </h2>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-[#786849]">
        {result.identity_rationale}
      </p>
      <Link
        className="mt-5 inline-flex min-h-11 items-center rounded-full bg-[#76541f] px-5 text-sm font-semibold text-white"
        href="/review"
      >
        Review Career Memory
      </Link>
    </section>
  );
}

function DiagnosisBrief({ result }: { result: DiagnosisResult }) {
  return (
    <div className="mt-5 space-y-5">
      <section className="rounded-[30px] bg-[#173f35] p-6 text-white sm:p-8">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#a7d8bd]">
              Strongest career identity
            </p>
            <h2 className="mt-3 max-w-4xl text-3xl font-semibold tracking-[-0.025em] sm:text-4xl">
              {result.career_identity}
            </h2>
          </div>
          <span className="shrink-0 rounded-full bg-white/10 px-3 py-2 text-xs font-semibold text-[#d8eee1]">
            {diagnosisConfidenceLabel(result.confidence)} · {Math.round(result.confidence * 100)}%
          </span>
        </div>
        <p className="mt-5 max-w-4xl text-sm leading-6 text-[#d4e7dd]">
          {result.identity_rationale}
        </p>
        <p className="mt-5 text-xs font-semibold text-[#a7d8bd]">
          Approved-memory-only · {result.evidence_ids.length} evidence reference
          {result.evidence_ids.length === 1 ? "" : "s"} · {result.diagnosis_version}
        </p>
      </section>

      <EvidenceMap result={result} />

      <OutcomeSignals signals={result.outcome_signals} />

      <div className="grid gap-5 lg:grid-cols-2">
        <BriefPanel eyebrow="Recognition Gap" title="What is not being recognized yet">
          <p className="text-sm leading-7 text-[#5e7169]">{result.recognition_gap}</p>
        </BriefPanel>
        <BriefPanel eyebrow="Missing proof" title="The smallest gaps worth closing">
          <ul className="space-y-3">
            {result.missing_proof.map((item) => (
              <li className="flex gap-3 text-sm leading-6 text-[#5e7169]" key={item}>
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[#4a8a6d]" />
                {item}
              </li>
            ))}
          </ul>
        </BriefPanel>
      </div>

      <ProofSprintPanel result={result} />

      <section className="rounded-[26px] border border-[#e2cfaa] bg-[#fff7e7] p-6">
        <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#956b2d]">
          What CareerOS thinks you should stop doing
        </p>
        <p className="mt-3 text-lg font-semibold leading-7 text-[#63481f]">
          {result.do_not_waste_time}
        </p>
      </section>

      <div className="grid gap-5 lg:grid-cols-[0.75fr_1.25fr]">
        <BriefPanel eyebrow="Exact next actions" title="Do these in order">
          <ol className="space-y-3">
            {result.exact_next_actions.map((action, index) => (
              <li className="flex gap-3 text-sm leading-6 text-[#5e7169]" key={action}>
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[#e9f3ed] text-xs font-bold text-[#397156]">
                  {index + 1}
                </span>
                {action}
              </li>
            ))}
          </ol>
        </BriefPanel>
        <ExactMessages messages={result.exact_messages} />
      </div>
    </div>
  );
}

function OutcomeSignals({ signals }: { signals: DiagnosisResult["outcome_signals"] }) {
  if (!signals.length) return null;
  return (
    <section className="rounded-[28px] border border-[#d9d2ec] bg-[#f7f4fc] p-6 sm:p-7">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#76609b]">
        Outcome signals · not canonical proof
      </p>
      <h2 className="mt-1 text-2xl font-semibold text-[#33284a]">
        Approved results that can guide strategy
      </h2>
      <div className="mt-5 space-y-4">
        {signals.map((signal) => (
          <article
            className="rounded-2xl border border-[#e2dcf0] bg-white/80 p-5"
            key={signal.feedback_event_id}
          >
            <p className="text-sm font-semibold leading-6 text-[#4d4067]">
              {signal.summary}
            </p>
            <p className="mt-2 text-sm leading-6 text-[#665b7d]">
              Future use: {signal.guidance}
            </p>
            <p className="mt-3 text-xs leading-5 text-[#817694]">
              {signal.caveat}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}

function EvidenceMap({ result }: { result: DiagnosisResult }) {
  return (
    <section className="rounded-[28px] border border-[#dce4df] bg-white p-6 sm:p-7">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7d8e87]">
        Evidence Map
      </p>
      <h2 className="mt-1 text-2xl font-semibold text-[#17362d]">
        Approved proof behind the judgment
      </h2>
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        {result.evidence_map.map((item) => (
          <article
            className="rounded-2xl border border-[#e1e8e4] bg-[#fbfcfa] p-5"
            key={item.memory_id}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-semibold text-[#29483e]">{item.memory_title}</h3>
                <p className="mt-1 text-[10px] font-bold uppercase tracking-[0.12em] text-[#608074]">
                  {item.memory_type.replaceAll("_", " ")}
                </p>
              </div>
              <span className="shrink-0 rounded-full bg-[#e7f2eb] px-2.5 py-1 text-[10px] font-bold text-[#356b51]">
                {evidenceStrengthLabel(item.strength)}
              </span>
            </div>
            <p className="mt-3 text-sm leading-6 text-[#5f716a]">
              {item.claim_supported}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {item.relevant_themes.map((theme) => (
                <span
                  className="rounded-full bg-white px-2.5 py-1 text-[11px] font-semibold text-[#547166] ring-1 ring-[#dce5e0]"
                  key={theme}
                >
                  {theme}
                </span>
              ))}
            </div>
            <p className="mt-3 text-xs text-[#819089]">
              {item.evidence_ids.length} evidence reference
              {item.evidence_ids.length === 1 ? "" : "s"} · {Math.round(item.confidence * 100)}% memory confidence
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}

function ProofSprintPanel({ result }: { result: DiagnosisResult }) {
  const sprint = result.proof_sprint;
  return (
    <section className="rounded-[28px] border border-[#cbded3] bg-[#edf6f0] p-6 sm:p-8">
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#3f8064]">
        7-day Proof Sprint
      </p>
      <h2 className="mt-2 text-2xl font-semibold text-[#17362d]">{sprint.objective}</h2>
      <p className="mt-3 max-w-4xl text-sm leading-6 text-[#587066]">
        {sprint.why_it_matters}
      </p>
      <div className="mt-6 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <ol className="space-y-3">
          {sprint.actions.map((action) => (
            <li className="rounded-2xl bg-white/80 px-4 py-3 text-sm leading-6 text-[#476057]" key={action}>
              {action}
            </li>
          ))}
        </ol>
        <div className="space-y-4">
          <SprintDetail label="Expected artifact" value={sprint.expected_artifact} />
          <SprintDetail label="How to use it" value={sprint.application_use} />
        </div>
      </div>
    </section>
  );
}

function SprintDetail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-[#d5e5dc] bg-white p-4">
      <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#668076]">
        {label}
      </p>
      <p className="mt-2 text-sm leading-6 text-[#4e655c]">{value}</p>
    </div>
  );
}

function ExactMessages({ messages }: { messages: Record<string, string> }) {
  const labels: Record<string, string> = {
    linkedin_outreach: "LinkedIn outreach",
    email_or_referral: "Email / referral / mentor",
    application_positioning: "Application positioning snippet",
  };
  return (
    <BriefPanel eyebrow="Exact next messages" title="Copy, personalize, and review">
      <div className="space-y-4">
        {Object.entries(messages).map(([key, message]) => (
          <article className="rounded-2xl border border-[#e0e7e3] bg-[#fbfcfa] p-4" key={key}>
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#567266]">
                {labels[key] ?? key.replaceAll("_", " ")}
              </p>
              <CopyButton value={message} />
            </div>
            <p className="mt-3 whitespace-pre-line text-sm leading-6 text-[#5b6f66]">
              {message}
            </p>
          </article>
        ))}
      </div>
    </BriefPanel>
  );
}

function CopyButton({ value }: { value: string }) {
  const [label, setLabel] = useState("Copy");
  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setLabel("Copied");
    } catch {
      setLabel("Copy unavailable");
    }
    window.setTimeout(() => setLabel("Copy"), 1600);
  }
  return (
    <button
      className="rounded-full border border-[#cbd9d1] bg-white px-3 py-1 text-[10px] font-bold text-[#4e7563]"
      onClick={() => void copy()}
      type="button"
    >
      {label}
    </button>
  );
}

function BriefPanel({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-[26px] border border-[#dce4df] bg-white p-6">
      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7d8e87]">
        {eyebrow}
      </p>
      <h2 className="mt-1 text-xl font-semibold text-[#17362d]">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function TeachCareerOSPanel({
  events,
  note,
  onChangeNote,
  onChangeStatus,
  onEdit,
  onTeach,
  teaching,
}: {
  events: CareerFeedbackEvent[];
  note: string;
  onChangeNote: (value: string) => void;
  onChangeStatus: (
    event: CareerFeedbackEvent,
    status: FeedbackEventStatus,
  ) => Promise<void>;
  onEdit: (event: CareerFeedbackEvent, rawNote: string) => Promise<boolean>;
  onTeach: () => Promise<void>;
  teaching: boolean;
}) {
  const [editingEventId, setEditingEventId] = useState<string | null>(null);
  const [editNote, setEditNote] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);

  function beginEdit(event: CareerFeedbackEvent) {
    setEditingEventId(event.id);
    setEditNote(event.raw_note);
  }

  async function saveEdit(event: CareerFeedbackEvent) {
    setSavingEdit(true);
    const saved = await onEdit(event, editNote);
    setSavingEdit(false);
    if (saved) {
      setEditingEventId(null);
      setEditNote("");
    }
  }

  return (
    <section className="mt-5 rounded-[28px] border border-[#dce4df] bg-white p-6 sm:p-8">
      <div className="grid gap-7 lg:grid-cols-[0.9fr_1.1fr]">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#3f8064]">
            Teach CareerOS
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-[#17362d]">
            Record what happened or how proof should be used
          </h2>
          <p className="mt-3 text-sm leading-6 text-[#687a73]">
            Notes begin as proposed learning events. They never rewrite the
            historical application or become canonical facts automatically.
          </p>
          <textarea
            aria-label="Teach CareerOS note"
            className="mt-5 min-h-36 w-full resize-y rounded-2xl border border-[#cfdbd4] bg-[#fbfcfa] p-4 text-sm leading-6 text-[#29483e] outline-none ring-[#dceee5] placeholder:text-[#96a39d] focus:ring-4"
            onChange={(event) => onChangeNote(event.target.value)}
            placeholder="Example: This cover letter led to an interview invite."
            value={note}
          />
          <button
            className="mt-3 min-h-11 rounded-full bg-[#173f35] px-5 text-sm font-semibold text-white disabled:opacity-60"
            disabled={teaching}
            onClick={() => void onTeach()}
            type="button"
          >
            {teaching ? "Saving feedback…" : "Save and teach"}
          </button>
        </div>
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7d8e87]">
            Recent feedback events
          </p>
          <div className="mt-3 space-y-3">
            {!events.length && (
              <p className="rounded-2xl bg-[#f7f9f6] p-4 text-sm text-[#75857e]">
                No feedback events yet. Add an outcome, framing rule, or draft
                preference when you learn something useful.
              </p>
            )}
            {events.map((event) => (
              <article className="rounded-2xl border border-[#e1e8e4] bg-[#fbfcfa] p-4" key={event.id}>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-[#e9f3ed] px-2.5 py-1 text-[10px] font-bold text-[#3e7159]">
                    {feedbackEventTypeLabel(event.event_type)}
                  </span>
                  <span className="rounded-full bg-white px-2.5 py-1 text-[10px] font-bold text-[#73847d] ring-1 ring-[#dce4df]">
                    {feedbackStatusLabel(event.status)}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-[#50665d]">
                  {event.structured_summary}
                </p>
                {event.artifact_label && (
                  <p className="mt-2 text-xs font-semibold text-[#667970]">
                    Artifact: {event.artifact_label}
                    {event.outcome
                      ? ` · Outcome: ${event.outcome.replaceAll("_", " ").toLowerCase()}`
                      : ""}
                  </p>
                )}
                <p className="mt-2 text-xs leading-5 text-[#7a8983]">
                  Future use: {event.suggested_future_use}
                </p>
                <p className="mt-2 text-xs font-semibold leading-5 text-[#64766f]">
                  {event.status === "APPROVED"
                    ? "Approved guidance can influence future diagnosis; artifact outcomes remain labeled signals, not proof."
                    : event.status === "ARCHIVED"
                      ? "Archived events are excluded from future diagnosis guidance."
                      : "Proposed events wait for your review before guiding diagnosis."}
                </p>
                {editingEventId === event.id ? (
                  <div className="mt-4 rounded-2xl border border-[#d8e2dc] bg-white p-3">
                    <label className="text-xs font-bold text-[#48675a]">
                      Correct feedback event
                      <textarea
                        aria-label="Edit feedback event note"
                        className="mt-2 min-h-28 w-full resize-y rounded-xl border border-[#cfdbd4] bg-[#fbfcfa] p-3 text-sm font-normal leading-6 text-[#29483e] outline-none"
                        onChange={(event) => setEditNote(event.target.value)}
                        value={editNote}
                      />
                    </label>
                    <div className="mt-2 flex gap-2">
                      <button
                        className="rounded-full bg-[#285b4a] px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
                        disabled={savingEdit}
                        onClick={() => void saveEdit(event)}
                        type="button"
                      >
                        {savingEdit ? "Saving…" : "Save changes"}
                      </button>
                      <button
                        className="rounded-full border border-[#d8ddd9] px-3 py-1.5 text-xs font-semibold text-[#6d7c76]"
                        disabled={savingEdit}
                        onClick={() => {
                          setEditingEventId(null);
                          setEditNote("");
                        }}
                        type="button"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      className="rounded-full border border-[#c9d9d0] px-3 py-1.5 text-xs font-semibold text-[#456b59]"
                      onClick={() => beginEdit(event)}
                      type="button"
                    >
                      Edit event
                    </button>
                    {event.status === "PROPOSED" && (
                      <>
                        <button
                          className="rounded-full bg-[#285b4a] px-3 py-1.5 text-xs font-semibold text-white"
                          onClick={() => void onChangeStatus(event, "APPROVED")}
                          type="button"
                        >
                          Approve guidance
                        </button>
                        <button
                          className="rounded-full border border-[#d8ddd9] px-3 py-1.5 text-xs font-semibold text-[#6d7c76]"
                          onClick={() => void onChangeStatus(event, "ARCHIVED")}
                          type="button"
                        >
                          Archive
                        </button>
                      </>
                    )}
                    {event.status === "APPROVED" && (
                      <button
                        className="rounded-full border border-[#d8ddd9] px-3 py-1.5 text-xs font-semibold text-[#6d7c76]"
                        onClick={() => void onChangeStatus(event, "ARCHIVED")}
                        type="button"
                      >
                        Archive
                      </button>
                    )}
                  </div>
                )}
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "CareerOS could not complete that diagnosis action.";
}
