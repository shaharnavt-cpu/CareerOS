"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { ChatPanel } from "@/components/chat/chat-panel";
import { KnowledgePanel } from "@/components/knowledge/knowledge-panel";
import { knowledgeItems } from "@/lib/onboarding-data";

export function OnboardingWorkspace() {
  const [stage, setStage] = useState(1);
  const visibleItems = useMemo(
    () => knowledgeItems.filter((item) => item.stage <= stage),
    [stage],
  );

  return (
    <main className="mx-auto max-w-[1500px] px-4 py-5 sm:px-6 lg:px-8">
      <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#488069]">
            Conversation first
          </p>
          <p className="mt-1 text-sm text-[#70817a]">
            Speak naturally. CareerOS organizes the details beside you.
          </p>
        </div>
        <Link
          className="inline-flex min-h-10 items-center justify-center gap-2 self-start rounded-full border border-[#cbdad2] bg-white px-4 text-xs font-semibold text-[#2f5d4d] shadow-sm transition hover:border-[#80ad99] hover:bg-[#f4faf6] sm:self-auto"
          href="/review"
        >
          Review {visibleItems.length} items
          <span aria-hidden="true">→</span>
        </Link>
      </div>
      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(340px,0.65fr)]">
        <ChatPanel onProgress={setStage} />
        <KnowledgePanel items={visibleItems} stage={stage} />
      </div>
    </main>
  );
}
