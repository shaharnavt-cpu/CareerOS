"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Brand } from "@/components/common/brand";
import {
  CareerOSApiError,
  getApiDiagnostics,
  getHealth,
  type HealthResponse,
  type ListeningJob,
  listListeningJobs,
  retryListeningJob,
} from "@/lib/knowledge-api";
import {
  friendlyFailureMessage,
  listeningStageLabel,
} from "@/lib/listening-utils";

const groups: Array<{
  key: ListeningJob["status"];
  label: string;
}> = [
  { key: "QUEUED", label: "Queued" },
  { key: "ACTIVE", label: "Active" },
  { key: "FAILED", label: "Failed" },
  { key: "COMPLETE", label: "Completed" },
];

function duration(milliseconds: number) {
  if (milliseconds < 1000) return `${Math.round(milliseconds)} ms`;
  return `${(milliseconds / 1000).toFixed(1)} s`;
}

export function ListeningDashboard() {
  const [jobs, setJobs] = useState<ListeningJob[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [developerMode, setDeveloperMode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiResponses, setApiResponses] = useState(getApiDiagnostics());

  const refresh = useCallback(async (refreshDatabase = false) => {
    try {
      const [nextJobs, nextHealth] = await Promise.all([
        listListeningJobs(developerMode),
        getHealth(developerMode, refreshDatabase),
      ]);
      setJobs(nextJobs);
      setHealth(nextHealth);
      setError(null);
    } catch (reason) {
      setError(
        reason instanceof CareerOSApiError
          ? reason.message
          : "Diagnostics are temporarily unavailable.",
      );
    } finally {
      setApiResponses(getApiDiagnostics());
    }
  }, [developerMode]);

  useEffect(() => {
    const initial = window.setTimeout(() => void refresh(false), 0);
    const interval = window.setInterval(() => void refresh(false), 1500);
    return () => {
      window.clearTimeout(initial);
      window.clearInterval(interval);
    };
  }, [refresh]);

  async function retry(jobId: string) {
    try {
      await retryListeningJob(jobId);
      await refresh(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Retry failed.");
    }
  }

  return (
    <main className="min-h-screen bg-[#f3f5f0] text-[#18352c]">
      <header className="border-b border-[#d9e3dd] bg-white/85 px-5 py-4 backdrop-blur sm:px-8">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-4">
          <Brand />
          <div className="flex items-center gap-3">
            <label className="flex cursor-pointer items-center gap-2 text-xs font-semibold text-[#526b61]">
              <input
                checked={developerMode}
                className="h-4 w-4 accent-[#245b48]"
                onChange={(event) => setDeveloperMode(event.target.checked)}
                type="checkbox"
              />
              Developer mode
            </label>
            <Link
              className="rounded-full border border-[#cedbd4] bg-white px-4 py-2 text-xs font-semibold text-[#315e4c] hover:bg-[#f2f8f4]"
              href="/onboarding"
            >
              Back to conversation
            </Link>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[1500px] px-4 py-7 sm:px-6 lg:px-8">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.15em] text-[#4b826b]">
              Intelligence observability
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-[-0.035em]">
              Listening Dashboard
            </h1>
            <p className="mt-2 text-sm text-[#687a73]">
              See exactly where every source stopped—without reading backend logs.
            </p>
          </div>
          <button
            className="self-start rounded-full bg-[#173f35] px-4 py-2 text-xs font-semibold text-white hover:bg-[#245b4b] sm:self-auto"
            onClick={() => void refresh(true)}
            type="button"
          >
            Refresh now
          </button>
        </div>

        <section
          className={`mt-6 rounded-2xl border p-4 ${
            health?.database.status === "available"
              ? "border-[#cce2d6] bg-[#f3faf6]"
              : "border-[#e5c8bd] bg-[#fff7f3]"
          }`}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.1em]">
                PostgreSQL · {health?.database.status ?? "checking"}
              </p>
              <p className="mt-1 text-xs text-[#64766f]">
                {health?.database.message ??
                  "Checking whether Career Memory can accept evidence."}
              </p>
            </div>
            <span className="text-xs font-semibold text-[#6b7c75]">
              {health?.database.latency_ms != null
                ? `${health.database.latency_ms} ms`
                : "—"}
            </span>
          </div>
          {developerMode && health?.database.developer_message && (
            <pre className="mt-3 max-h-44 overflow-auto whitespace-pre-wrap rounded-xl bg-[#2b302e] p-3 text-[11px] leading-5 text-[#d9e5df]">
              {health.database.developer_message}
            </pre>
          )}
        </section>

        {error && (
          <p className="mt-4 rounded-xl border border-[#e3c9bf] bg-[#fff8f5] px-4 py-3 text-sm text-[#955646]">
            {error}
          </p>
        )}

        <section className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {groups.map((group) => (
            <div
              className="rounded-2xl border border-[#d7e1db] bg-white p-4"
              key={group.key}
            >
              <p className="text-xs font-semibold text-[#718179]">{group.label}</p>
              <p className="mt-2 text-3xl font-semibold">
                {jobs.filter((job) => job.status === group.key).length}
              </p>
            </div>
          ))}
        </section>

        <div className="mt-6 space-y-7">
          {groups.map((group) => {
            const grouped = jobs.filter((job) => job.status === group.key);
            return (
              <section key={group.key}>
                <h2 className="text-sm font-bold uppercase tracking-[0.12em] text-[#587067]">
                  {group.label} · {grouped.length}
                </h2>
                <div className="mt-3 grid gap-4 xl:grid-cols-2">
                  {!grouped.length && (
                    <p className="rounded-2xl border border-dashed border-[#d4ddd8] px-4 py-6 text-center text-xs text-[#89958f] xl:col-span-2">
                      No {group.label.toLowerCase()} jobs.
                    </p>
                  )}
                  {grouped.map((job) => (
                    <article
                      className="rounded-2xl border border-[#d6e0da] bg-white p-5 shadow-[0_16px_45px_-38px_rgba(20,58,46,0.7)]"
                      key={job.id}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <h3 className="truncate text-sm font-semibold">
                            {job.filename}
                          </h3>
                          <p className="mt-1 text-xs text-[#6e8078]">
                            Current stage: {listeningStageLabel(job.current_stage)}
                          </p>
                        </div>
                        <span className="rounded-full bg-[#edf4f0] px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.08em] text-[#4e725f]">
                          {duration(job.elapsed_ms)}
                        </span>
                      </div>

                      <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                        <Metric label="Characters" value={job.extracted_character_count} />
                        <Metric label="Evidence" value={job.evidence_count} />
                        <Metric label="Retries" value={job.retry_count} />
                      </div>

                      <ol className="mt-4 space-y-2 border-l border-[#d9e3dd] pl-4">
                        {job.stages.map((stage) => (
                          <li className="text-xs" key={stage.stage}>
                            <div className="flex items-center justify-between gap-3">
                              <span
                                className={
                                  stage.status === "FAILED"
                                    ? "font-semibold text-[#a45746]"
                                    : stage.status === "ACTIVE"
                                      ? "font-semibold text-[#28634b]"
                                      : stage.status === "COMPLETE"
                                        ? "text-[#526b61]"
                                        : "text-[#9ca8a2]"
                                }
                              >
                                {stage.status === "COMPLETE"
                                  ? "✓"
                                  : stage.status === "ACTIVE"
                                    ? "→"
                                    : stage.status === "FAILED"
                                      ? "!"
                                      : "○"}{" "}
                                {listeningStageLabel(stage.stage)}
                              </span>
                              <span className="text-[10px] text-[#8a9892]">
                                {stage.duration_ms != null
                                  ? duration(stage.duration_ms)
                                  : ""}
                              </span>
                            </div>
                          </li>
                        ))}
                      </ol>

                      {job.failure && (
                        <div className="mt-4 rounded-xl border border-[#e5c9bf] bg-[#fff8f5] p-3">
                          <p className="text-xs font-bold text-[#9b5545]">
                            {job.failure.code}
                          </p>
                          <p className="mt-1 text-xs leading-5 text-[#815f56]">
                            {friendlyFailureMessage(job.failure.code)}
                          </p>
                          {job.failure.retryable && (
                            <button
                              className="mt-3 rounded-full bg-[#8c5144] px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.08em] text-white"
                              onClick={() => void retry(job.id)}
                              type="button"
                            >
                              Retry from checkpoint
                            </button>
                          )}
                        </div>
                      )}

                      {developerMode && job.diagnostics && (
                        <details className="mt-4 rounded-xl bg-[#29302d] p-3 text-[#dce8e1]">
                          <summary className="cursor-pointer text-xs font-semibold">
                            Developer logs
                          </summary>
                          <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap text-[10px] leading-5">
                            {JSON.stringify(job.diagnostics.developer_logs, null, 2)}
                            {job.failure?.stack_trace
                              ? `\n\nSTACK TRACE\n${job.failure.stack_trace}`
                              : ""}
                          </pre>
                        </details>
                      )}
                    </article>
                  ))}
                </div>
              </section>
            );
          })}
        </div>

        {developerMode && (
          <section className="mt-8 rounded-2xl bg-[#252b28] p-5 text-[#dbe7e1]">
            <h2 className="text-sm font-semibold">Recent API responses</h2>
            <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap text-[10px] leading-5">
              {JSON.stringify(apiResponses, null, 2)}
            </pre>
          </section>
        )}
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl bg-[#f4f7f4] px-2 py-2.5">
      <p className="text-sm font-semibold">{value.toLocaleString()}</p>
      <p className="mt-0.5 text-[10px] uppercase tracking-[0.08em] text-[#7e8d86]">
        {label}
      </p>
    </div>
  );
}
