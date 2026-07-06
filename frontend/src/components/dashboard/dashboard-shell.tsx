import Link from "next/link";

import { KnowledgeSummary } from "@/components/dashboard/knowledge-summary";
import { ProfileCompleteness } from "@/components/dashboard/profile-completeness";

const nextActions = [
  {
    title: "Clarify your GEVIP dates",
    detail: "One Program detail needs review",
    action: "2 min",
  },
  {
    title: "Add evidence for leadership",
    detail: "A certificate, project, or story works",
    action: "5 min",
  },
  {
    title: "Describe your AAS presentation",
    detail: "Add the title and conference date",
    action: "3 min",
  },
];

const activity = [
  ["Profile review completed", "Just now"],
  ["Scientific communication added", "3 min ago"],
  ["GEVIP connected to capstone", "6 min ago"],
  ["Guided Story started", "9 min ago"],
];

export function DashboardShell() {
  return (
    <main className="mx-auto max-w-7xl px-5 py-10 sm:px-8 lg:py-14">
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-[#3f8064]">
            Career profile
          </p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.045em] text-[#142f26] sm:text-5xl">
            Good morning, Arnav.
          </h1>
          <p className="mt-3 text-base text-[#6d7e77]">
            Your career memory is becoming clearer with every detail.
          </p>
        </div>
        <Link
          className="inline-flex min-h-11 items-center justify-center rounded-full border border-[#bfd4c8] bg-white px-5 text-sm font-semibold text-[#2e654f] transition hover:bg-[#eff8f2]"
          href="/onboarding"
        >
          Continue Guided Story
        </Link>
        <Link
          className="inline-flex min-h-11 items-center justify-center rounded-full bg-[#173f35] px-5 text-sm font-semibold text-white transition hover:bg-[#285b4a]"
          href="/stories"
        >
          Open Story Workspace
        </Link>
      </div>

      <div className="mt-9 grid gap-5 lg:grid-cols-2">
        <ProfileCompleteness />
        <KnowledgeSummary />
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
        <section className="rounded-[26px] border border-[#dce4df] bg-white p-5 sm:p-6">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7d8e87]">
            Suggested next actions
          </p>
          <h2 className="mt-1 text-xl font-semibold text-[#17362d]">
            Keep the momentum going
          </h2>
          <div className="mt-5 space-y-2.5">
            {nextActions.map((item, index) => (
              <article
                className="group flex items-center gap-4 rounded-2xl border border-[#e1e7e3] p-4 transition hover:border-[#a9c9b9] hover:bg-[#f8fbf8]"
                key={item.title}
              >
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#edf5f0] text-xs font-bold text-[#3f785f]">
                  0{index + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <h3 className="text-sm font-semibold text-[#26463b]">
                    {item.title}
                  </h3>
                  <p className="mt-0.5 text-xs text-[#83918c]">{item.detail}</p>
                </div>
                <span className="rounded-full bg-[#f0f3f0] px-2.5 py-1 text-[10px] font-bold text-[#7b8883]">
                  {item.action}
                </span>
              </article>
            ))}
          </div>
        </section>

        <section className="rounded-[26px] border border-[#dce4df] bg-[#f9faf7] p-5 sm:p-6">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7d8e87]">
            Recent activity
          </p>
          <h2 className="mt-1 text-xl font-semibold text-[#17362d]">
            Your profile timeline
          </h2>
          <ol className="mt-5 space-y-1">
            {activity.map(([label, time], index) => (
              <li className="relative flex gap-3 pb-5" key={label}>
                {index < activity.length - 1 && (
                  <span className="absolute left-[5px] top-4 h-full w-px bg-[#d7e2dc]" />
                )}
                <span className="relative mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full bg-[#5b9b7d] ring-4 ring-[#e5f2eb]" />
                <div>
                  <p className="text-sm font-medium text-[#3a5048]">{label}</p>
                  <time className="mt-0.5 block text-[11px] text-[#8e9b96]">
                    {time}
                  </time>
                </div>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </main>
  );
}
