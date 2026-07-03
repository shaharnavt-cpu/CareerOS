"use client";

import { useRouter } from "next/navigation";
import { ChangeEvent, useRef, useState } from "react";

import {
  saveUploadedSource,
  type SourceType,
} from "@/lib/knowledge-api";

const sourceTypes: { value: SourceType; label: string }[] = [
  { value: "RESUME", label: "Resume or CV" },
  { value: "TRANSCRIPT", label: "Transcript" },
  { value: "LINKEDIN", label: "LinkedIn / profile" },
  { value: "MANUAL", label: "Manual entry" },
  { value: "CONVERSATION", label: "Conversation" },
  { value: "GENERIC_DOCUMENT", label: "Generic document" },
];

export function UploadZone() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [sourceType, setSourceType] = useState<SourceType>("RESUME");
  const [label, setLabel] = useState("My resume");
  const [text, setText] = useState("");
  const [filename, setFilename] = useState<string>();
  const [status, setStatus] = useState(
    "Paste text or choose a text-based document",
  );

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setStatus(`Opening ${file.name}…`);
    try {
      const source = await file.text();
      if (!source.trim()) throw new Error("The selected file is empty.");
      setText(source);
      setFilename(file.name);
      if (label === "My resume") setLabel(file.name.replace(/\.[^.]+$/, ""));
      setStatus(`${file.name} is ready for listening`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not read that file.");
    }
  }

  function continueToListening() {
    if (!text.trim()) {
      setStatus("Paste source text or choose a file first.");
      return;
    }
    if (!label.trim()) {
      setStatus("Give this source a short label first.");
      return;
    }
    saveUploadedSource({
      raw_text: text,
      source_type: sourceType,
      label: label.trim(),
      original_filename: filename,
      media_type: filename?.endsWith(".md") ? "text/markdown" : "text/plain",
    });
    router.push("/onboarding");
  }

  return (
    <div className="relative overflow-hidden rounded-[28px] border border-[#c5d7ce] bg-white/85 p-6 shadow-[0_24px_60px_-40px_rgba(31,64,53,0.55)]">
      <div className="absolute -right-8 -top-8 h-28 w-28 rounded-full bg-[#dff2e8] blur-2xl" />
      <div className="relative">
        <div className="flex items-center gap-3">
          <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-[#edf7f1] text-[#2f7158] ring-1 ring-[#cfe5d9]">
            <svg
              aria-hidden="true"
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              viewBox="0 0 24 24"
            >
              <path
                d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 13v5a2 2 0 002 2h10a2 2 0 002-2v-5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          <div>
            <h2 className="text-lg font-semibold text-[#17362d]">
              Add a source
            </h2>
            <p className="text-sm text-[#677872]">
              CareerOS keeps its label and provenance attached.
            </p>
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <label className="text-xs font-semibold text-[#496159]">
            Source type
            <select
              className="mt-1.5 w-full rounded-xl border border-[#d4dfd9] bg-white px-3 py-2.5 text-sm font-normal text-[#244238] outline-none focus:border-[#68a087] focus:ring-4 focus:ring-[#e1f0e8]"
              onChange={(event) => setSourceType(event.target.value as SourceType)}
              value={sourceType}
            >
              {sourceTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-semibold text-[#496159]">
            Source label
            <input
              className="mt-1.5 w-full rounded-xl border border-[#d4dfd9] px-3 py-2.5 text-sm font-normal text-[#244238] outline-none focus:border-[#68a087] focus:ring-4 focus:ring-[#e1f0e8]"
              maxLength={256}
              onChange={(event) => setLabel(event.target.value)}
              placeholder="e.g. July resume"
              value={label}
            />
          </label>
        </div>

        <label className="mt-4 block text-xs font-semibold text-[#496159]">
          Source text
          <textarea
            className="mt-1.5 min-h-32 w-full resize-y rounded-2xl border border-[#d4dfd9] bg-[#fbfcfa] px-4 py-3 text-sm font-normal leading-6 text-[#244238] outline-none placeholder:text-[#98a59f] focus:border-[#68a087] focus:ring-4 focus:ring-[#e1f0e8]"
            onChange={(event) => setText(event.target.value)}
            placeholder="Paste a resume, transcript, profile, conversation, or document…"
            value={text}
          />
        </label>

        <input
          accept=".txt,.md,.csv,text/plain,text/markdown,text/csv"
          className="sr-only"
          onChange={(event) => void handleFile(event)}
          ref={inputRef}
          type="file"
        />
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button
            className="rounded-full border border-[#cbdad2] bg-white px-4 py-2.5 text-xs font-semibold text-[#35614f] transition hover:border-[#80ad99] hover:bg-[#f4faf6]"
            onClick={() => inputRef.current?.click()}
            type="button"
          >
            Choose text file
          </button>
          <button
            className="rounded-full bg-[#173f35] px-5 py-2.5 text-xs font-semibold text-white transition hover:bg-[#245b4b]"
            onClick={continueToListening}
            type="button"
          >
            Listen to this source
          </button>
        </div>
        <p
          aria-live="polite"
          className="mt-4 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#71857c]"
        >
          {status}
        </p>
      </div>
    </div>
  );
}
