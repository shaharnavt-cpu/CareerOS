"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("CareerOS workspace error", error);
  }, [error]);

  return (
    <main className="grid min-h-screen place-items-center bg-[#f6f7f2] px-5">
      <section className="max-w-xl rounded-[28px] border border-[#dce4df] bg-white p-8 text-center shadow-[0_20px_70px_-45px_rgba(23,63,53,0.85)]">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#3f8064]">
          Workspace interrupted
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-[#142f26]">
          CareerOS could not load this workspace.
        </h1>
        <p className="mt-3 text-sm leading-6 text-[#6d7e77]">
          Try refreshing this workspace, or return to the dashboard and pick up
          from your approved Career Memory.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <button
            className="rounded-full bg-[#173f35] px-5 py-2.5 text-sm font-semibold text-white"
            onClick={reset}
            type="button"
          >
            Try again
          </button>
          <Link
            className="rounded-full border border-[#c7d8cf] px-5 py-2.5 text-sm font-semibold text-[#35634f]"
            href="/dashboard"
          >
            Return to dashboard
          </Link>
        </div>
      </section>
    </main>
  );
}
