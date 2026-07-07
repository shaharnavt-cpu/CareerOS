"use client";

import type { ListeningJob } from "@/lib/knowledge-api";
import { listeningStageLabel } from "@/lib/listening-utils";

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
        <span className="rounded-full bg-[#edf5f0] px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.1em] text-[#4a7a65]">
          {jobs.length} {jobs.length === 1 ? "source" : "sources"}
        </span>
      </div>

      <div className="mt-3 max-h-64 space-y-2 overflow-y-auto">
        {!jobs.length && (
          <div className="rounded-2xl border border-dashed border-[#ccd9d2] bg-[#f7faf7] px-4 py-5 text-center text-xs leading-5 text-[#73827c]">
            Attach a resume, transcript, certificate, paper, portfolio, or job
            description from the conversation.
          </div>
        )}
        {jobs.map((job) => {
          const failed = job.stage === "FAILED";
          const complete = job.stage === "COMPLETE";
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
                    {job.message}
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
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[#e4ebe7]">
                <div
                  className={`h-full rounded-full transition-[width] duration-500 ${failed ? "bg-[#c87e6e]" : complete ? "bg-[#4f9a76]" : "bg-[#73a88e]"}`}
                  style={{ width: `${job.progress}%` }}
                />
              </div>
              <div className="mt-2 flex items-center justify-between gap-2 text-[10px] font-semibold uppercase tracking-[0.08em] text-[#7b8d85]">
                <span>{listeningStageLabel(job.stage)}</span>
                <span>
                  {job.document_type
                    ? job.document_type.replaceAll("_", " ")
                    : `${job.progress}%`}
                </span>
              </div>
              {failed && (
                <button
                  className="mt-2 rounded-full border border-[#d9c5be] bg-white px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.08em] text-[#8c5144] hover:bg-[#fff8f5]"
                  onClick={() => void onRetry(job.id)}
                  type="button"
                >
                  Try again
                </button>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
