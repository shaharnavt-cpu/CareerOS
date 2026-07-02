"use client";

import { useRouter } from "next/navigation";
import { ChangeEvent, useRef, useState } from "react";

import { saveUploadedSource } from "@/lib/knowledge-api";

const fileTypes = ["Text resume", "Markdown CV", "Transcript text"];

export function UploadZone() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState("Choose a text-based career document");

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setStatus(`Reading ${file.name}…`);
    try {
      const source = await file.text();
      if (!source.trim()) throw new Error("The selected file is empty.");
      saveUploadedSource(source);
      router.push("/onboarding");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not read that file.");
    }
  }

  return (
    <div
      aria-label="Document upload"
      className="group relative overflow-hidden rounded-[28px] border border-dashed border-[#9cb8ad] bg-white/75 p-7 shadow-[0_24px_60px_-40px_rgba(31,64,53,0.55)] transition-colors hover:border-[#4f8a72] hover:bg-white"
    >
      <div className="absolute -right-8 -top-8 h-28 w-28 rounded-full bg-[#dff2e8] blur-2xl" />
      <div className="relative flex flex-col items-center text-center">
        <span className="grid h-14 w-14 place-items-center rounded-2xl bg-[#edf7f1] text-[#2f7158] ring-1 ring-[#cfe5d9]">
          <svg
            aria-hidden="true"
            className="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="1.8"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 13v5a2 2 0 002 2h10a2 2 0 002-2v-5"
            />
          </svg>
        </span>
        <h2 className="mt-5 text-lg font-semibold text-[#17362d]">
          Bring what you already have
        </h2>
        <p className="mt-2 max-w-sm text-sm leading-6 text-[#677872]">
          Upload a text-based resume or CV. CareerOS will turn its contents into
          explainable proposals for your review.
        </p>
        <input
          accept=".txt,.md,.csv,text/plain,text/markdown,text/csv"
          className="sr-only"
          onChange={(event) => void handleFile(event)}
          ref={inputRef}
          type="file"
        />
        <button
          className="mt-5 rounded-full bg-[#173f35] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#245b4b]"
          onClick={() => inputRef.current?.click()}
          type="button"
        >
          Choose file
        </button>
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          {fileTypes.map((type) => (
            <span
              className="rounded-full border border-[#dbe5df] bg-[#f8faf7] px-3 py-1.5 text-xs font-medium text-[#51655e]"
              key={type}
            >
              {type}
            </span>
          ))}
        </div>
        <p
          aria-live="polite"
          className="mt-5 text-[11px] font-semibold uppercase tracking-[0.14em] text-[#71857c]"
        >
          {status}
        </p>
      </div>
    </div>
  );
}
