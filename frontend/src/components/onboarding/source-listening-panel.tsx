"use client";

import Link from "next/link";

import type { ListeningJob, StageTiming } from "@/lib/knowledge-api";
import {
  friendlyFailureMessage,
  listeningStageLabel,
} from "@/lib/listening-utils";

function stageIcon(stage: StageTiming) {
  if (stage.status === "COMPLETE") return "✓";
  if (stage.status === "ACTIVE") return "→";
  if (stage.status === "FAILED") return "!";
  return "○";
}

export function SourceListeningPanel({
  jobs,
  onRetry,
  onDismiss,
}: {
  jobs: ListeningJob[];
  onRetry: (jobId: string) => Promise<void>;
  onDismiss: (jobId: string) => void;
}) {
  return (
    <section className="rounded-[24px] border border-[#d7e2dc] bg-white/90 p-4 shadow-[0_18px_50px_-38px_rgba(20,58,46,0.7)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-[#193b30]">Sources</h2>
          <p className="mt-0.5 text-xs text-[#75857f]">
            Listening continues while you chat.
          </p>
        </div>
        <Link
          className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#4a7a65] hover:text-[#285943]"
          href="/listening"
        >
          Diagnostics
        </Link>
      </div>

      <div className="mt-3 max-h-[32rem] space-y-2 overflow-y-auto">
        {!jobs.length && (
          <div className="rounded-2xl border border-dashed border-[#ccd9d2] bg-[#f7faf7] px-4 py-5 text-center text-xs leading-5 text-[#73827c]">
            Attach a resume, transcript, certificate, paper, portfolio, or job
            description from the conversation.
          </div>
        )}
        {jobs.map((job) => {
          const failed = job.status === "FAILED";
          const complete = job.status === "COMPLETE";
          return (
            <article
              className="rounded-2xl border border-[#dde5e0] bg-[#fbfcfa] p-3"
              key={job.id}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-xs font-semibold text-[#29483e]">
                    {job.filename}
                  </p>
                  <p
                    className={`mt-0.5 text-[11px] ${failed ? "text-[#a25747]" : "text-[#70817a]"}`}
                  >
                    {failed && job.failure
                      ? friendlyFailureMessage(job.failure.code)
                      : job.message}
                  </p>
                </div>
                {(complete || failed) && (
                  <button
                    aria-label={`Dismiss ${job.filename}`}
                    className="shrink-0 text-sm text-[#91a099] hover:text-[#49665a]"
                    onClick={() => onDismiss(job.id)}
                    type="button"
                  >
                    ×
                  </button>
                )}
              </div>

              <ol className="mt-3 space-y-1.5 border-l border-[#dce5e0] pl-3">
                {job.stages.map((stage) => (
                  <li
                    className={`flex items-center gap-2 text-[11px] ${
                      stage.status === "ACTIVE"
                        ? "font-semibold text-[#2d6a51]"
                        : stage.status === "FAILED"
                          ? "font-semibold text-[#a25747]"
                          : stage.status === "COMPLETE"
                            ? "text-[#60776d]"
                            : "text-[#a0aaa5]"
                    }`}
                    key={stage.stage}
                  >
                    <span aria-hidden="true" className="w-3 text-center">
                      {stageIcon(stage)}
                    </span>
                    <span>
                      {stage.stage === "DETECT_DOCUMENT_TYPE" &&
                      stage.status === "COMPLETE"
                        ? stage.message
                        : listeningStageLabel(stage.stage)}
                    </span>
                  </li>
                ))}
              </ol>

              {failed && job.failure?.retryable && (
                <button
                  className="mt-3 rounded-full border border-[#d9c5be] bg-white px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.08em] text-[#8c5144] hover:bg-[#fff8f5]"
                  onClick={() => void onRetry(job.id)}
                  type="button"
                >
                  Retry from {listeningStageLabel(job.failure.stage)}
                </button>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
