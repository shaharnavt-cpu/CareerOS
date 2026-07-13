import Link from "next/link";

import { Brand } from "@/components/common/brand";

const links = [
  { href: "/dashboard", label: "Career Memory", key: "dashboard" },
  { href: "/diagnosis", label: "Diagnosis", key: "diagnosis" },
  { href: "/proof-artifacts", label: "Proof", key: "proof" },
  { href: "/review", label: "Review", key: "review" },
  { href: "/stories", label: "Stories", key: "stories" },
  { href: "/applications", label: "Applications", key: "applications" },
  { href: "/onboarding", label: "Listen", key: "onboarding" },
] as const;

export type WorkspaceNavKey = (typeof links)[number]["key"];

export function WorkspaceNav({ active }: { active?: WorkspaceNavKey }) {
  return (
    <header className="border-b border-[var(--cos-border)] bg-[color:var(--cos-surface)/0.95] px-5 py-4 backdrop-blur-xl sm:px-8">
      <div className="mx-auto flex max-w-[1500px] flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <Brand />
        <nav
          aria-label="CareerOS workspaces"
          className="flex flex-wrap items-center gap-2 text-sm font-semibold text-[#52665e]"
        >
          {links.map((link) =>
            link.key === active ? (
              <span
                className="rounded-full bg-[#173f35] px-4 py-2 text-white"
                key={link.key}
              >
                {link.label}
              </span>
            ) : (
              <Link
                className="rounded-full px-4 py-2 transition hover:bg-[#edf3ee]"
                href={link.href}
                key={link.key}
              >
                {link.label}
              </Link>
            ),
          )}
        </nav>
      </div>
    </header>
  );
}
