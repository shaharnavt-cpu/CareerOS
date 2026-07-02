"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { ChatPanel } from "@/components/chat/chat-panel";
import { KnowledgePanel } from "@/components/knowledge/knowledge-panel";
import { sampleCareerSource } from "@/lib/onboarding-data";
import {
  generateKnowledgeProposals,
  loadProposals,
  mergeProposals,
  type KnowledgeProposal,
  saveProposals,
  takeUploadedSource,
} from "@/lib/knowledge-api";

export function OnboardingWorkspace() {
  const [proposals, setProposals] = useState<KnowledgeProposal[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const initialized = useRef(false);

  const addProposals = useCallback((incoming: KnowledgeProposal[]) => {
    setProposals((current) => {
      const next = mergeProposals(current, incoming);
      saveProposals(next);
      return next;
    });
  }, []);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    let cancelled = false;

    async function initialize() {
      await Promise.resolve();
      const saved = loadProposals();
      if (saved.length) {
        if (!cancelled) {
          setProposals(saved);
          setIsLoading(false);
        }
        return;
      }

      const uploaded = takeUploadedSource();
      try {
        const result = await generateKnowledgeProposals({
          raw_source: uploaded ?? sampleCareerSource,
          source_type: "RESUME",
          source_name: uploaded ? "Uploaded resume" : "Sprint 4 sample resume",
        });
        if (!cancelled) addProposals(result.proposals);
      } catch (reason) {
        if (!cancelled) {
          setError(
            reason instanceof Error
              ? reason.message
              : "The reasoning engine is unavailable.",
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void initialize();
    return () => {
      cancelled = true;
    };
  }, [addProposals]);

  async function reasonAboutConversation(message: string) {
    const result = await generateKnowledgeProposals({
      raw_source: message,
      source_type: "CONVERSATION",
      source_name: "Guided Story conversation",
    });
    addProposals(result.proposals);
    const clarification = result.proposals.find(
      (proposal) => proposal.clarification,
    )?.clarification;
    if (clarification) return clarification.question;
    return result.proposals.length
      ? `I found ${result.proposals.length} explainable proposal${result.proposals.length === 1 ? "" : "s"}. Review the confidence and evidence beside our conversation.`
      : "I didn’t find a complete career entity in that message. Try naming the experience, project, skill, or achievement you want to capture.";
  }

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
          {isLoading && (
            <p className="mt-1 text-xs text-[#6f887e]">Analyzing source evidence…</p>
          )}
          {error && (
            <p className="mt-1 text-xs font-medium text-[#9a5c4e]">{error}</p>
          )}
        </div>
        <Link
          className="inline-flex min-h-10 items-center justify-center gap-2 self-start rounded-full border border-[#cbdad2] bg-white px-4 text-xs font-semibold text-[#2f5d4d] shadow-sm transition hover:border-[#80ad99] hover:bg-[#f4faf6] sm:self-auto"
          href="/review"
        >
          Review {proposals.length} items
          <span aria-hidden="true">→</span>
        </Link>
      </div>
      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(340px,0.65fr)]">
        <ChatPanel onReason={reasonAboutConversation} />
        <KnowledgePanel
          items={proposals}
          stage={Math.min(3, Math.max(1, Math.ceil(proposals.length / 2)))}
        />
      </div>
    </main>
  );
}
