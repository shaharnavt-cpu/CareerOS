import Link from "next/link";

import { Brand } from "@/components/common/brand";

const principles = [
  "Tell your story naturally",
  "Review what CareerOS understands",
  "You approve every fact",
];

export function WelcomeScreen() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-[#f6f7f1] text-[#152b25]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_12%_16%,rgba(183,224,203,0.45),transparent_30%),radial-gradient(circle_at_88%_80%,rgba(238,214,166,0.38),transparent_32%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(23,63,53,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(23,63,53,0.035)_1px,transparent_1px)] bg-[size:48px_48px]" />

      <div className="relative mx-auto flex min-h-screen max-w-[1440px] flex-col px-5 pb-8 pt-5 sm:px-8 lg:px-12">
        <header className="flex items-center justify-between">
          <Brand />
          <span className="rounded-full border border-[#d9e2dc] bg-white/70 px-3 py-1.5 text-xs font-semibold text-[#63766f] backdrop-blur">
            Guided Story · 6–8 min
          </span>
        </header>

        <section className="grid flex-1 items-center gap-12 py-12 lg:grid-cols-[1.05fr_0.95fr] lg:py-16">
          <div className="max-w-2xl">
            <p className="inline-flex items-center gap-2 rounded-full border border-[#c6ddcf] bg-[#eaf5ee] px-3 py-1.5 text-xs font-bold uppercase tracking-[0.15em] text-[#2f6b54]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#3f8969]" />
              Build your career memory
            </p>
            <h1 className="mt-7 text-5xl font-semibold leading-[1.02] tracking-[-0.055em] text-[#12271f] sm:text-6xl lg:text-7xl">
              Your story is more than a set of forms.
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-[#5c7068] sm:text-xl">
              CareerOS listens to your journey, organizes the connected facts,
              and gives you the final say before anything becomes part of your
              professional profile.
            </p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Link
                className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full bg-[#173f35] px-6 text-sm font-semibold text-white shadow-[0_16px_35px_-18px_rgba(23,63,53,0.8)] transition hover:-translate-y-0.5 hover:bg-[#205445] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#173f35]"
                href="/onboarding"
              >
                Start Conversation
                <span aria-hidden="true">→</span>
              </Link>
              <span className="text-sm text-[#71817b]">
                No documents required to begin
              </span>
            </div>

            <ul className="mt-10 grid gap-3 text-sm text-[#4f625b] sm:grid-cols-3">
              {principles.map((principle) => (
                <li className="flex items-start gap-2" key={principle}>
                  <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-[#dcefe5] text-[11px] font-bold text-[#2d6b52]">
                    ✓
                  </span>
                  {principle}
                </li>
              ))}
            </ul>
          </div>

          <div className="relative lg:pl-8">
            <div className="absolute -left-3 top-10 z-10 hidden rounded-2xl border border-white/70 bg-white/90 p-4 shadow-xl shadow-[#274b3e]/10 backdrop-blur sm:block lg:-left-8">
              <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-[#80918b]">
                Your control
              </p>
              <p className="mt-1 text-sm font-semibold text-[#24483c]">
                Nothing saves without approval
              </p>
            </div>
            <div className="relative overflow-hidden rounded-[28px] border border-[#c5d7ce] bg-white/85 p-7 shadow-[0_24px_60px_-40px_rgba(31,64,53,0.55)]">
              <div className="absolute -right-12 -top-12 h-40 w-40 rounded-full bg-[#dff2e8] blur-3xl" />
              <div className="relative">
                <span className="grid h-12 w-12 place-items-center rounded-2xl bg-[#edf7f1] text-[#2f7158] ring-1 ring-[#cfe5d9]">
                  <svg
                    aria-hidden="true"
                    className="h-6 w-6"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    viewBox="0 0 24 24"
                  >
                    <path
                      d="M9.5 12.5l5.4-5.4a3 3 0 114.2 4.2l-7.5 7.5a5 5 0 01-7.1-7.1l7.8-7.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
                <h2 className="mt-5 text-xl font-semibold text-[#17362d]">
                  Bring what you already have
                </h2>
                <p className="mt-2 text-sm leading-6 text-[#677872]">
                  Drop resumes, transcripts, certificates, papers, portfolios,
                  or job descriptions directly into the conversation. No separate
                  upload ritual. No manual classification.
                </p>
                <div className="mt-5 flex flex-wrap gap-2">
                  {["PDF", "DOCX", "TXT", "Markdown", "CSV"].map((format) => (
                    <span
                      className="rounded-full border border-[#d7e3dc] bg-[#f8fbf8] px-3 py-1.5 text-[11px] font-semibold text-[#4e6f61]"
                      key={format}
                    >
                      {format}
                    </span>
                  ))}
                </div>
                <p className="mt-5 text-xs font-medium text-[#4e7f69]">
                  Your conversation stays open while every source is heard.
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
