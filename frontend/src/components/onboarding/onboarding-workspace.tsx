"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { ChatPanel } from "@/components/chat/chat-panel";
import { KnowledgePanel } from "@/components/knowledge/knowledge-panel";
import { sampleCareerSource } from "@/lib/onboarding-data";
import { nextListeningStep } from "@/lib/listening-utils";
import {
  generateListeningProposals,
  loadProposals,
  type KnowledgeProposal,
  type PendingSource,
  rememberListeningSource,
  replacePendingProposals,
  saveProposals,
  submitListeningSource,
  takeUploadedSource,
} from "@/lib/knowledge-api";

const listeningStages = [
  "Listening to your source…",
  "Finding education and experience…",
  "Finding projects and skills…",
  "Comparing evidence…",
  "Preparing knowledge proposals…",
];

export function OnboardingWorkspace() {
  const [proposals, setProposals] = useState<KnowledgeProposal[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [listeningStep, setListeningStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const initialized = useRef(false);

  const addProposals = useCallback((incoming: KnowledgeProposal[]) => {
    setProposals((current) => {
      const next = replacePendingProposals(current, incoming);
      saveProposals(next);
      return next;
    });
  }, []);

  useEffect(() => {
    if (!isLoading) return;
    const interval = window.setInterval(
      () =>
        setListeningStep((current) =>
          nextListeningStep(current, listeningStages.length),
        ),
      650,
    );
    return () => window.clearInterval(interval);
  }, [isLoading]);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    let cancelled = false;

    async function initialize() {
      await Promise.resolve();
      const saved = loadProposals();
      const uploaded = takeUploadedSource();
      if (saved.length && !uploaded) {
        if (!cancelled) {
          setProposals(saved);
          setIsLoading(false);
        }
        return;
      }

      if (saved.length) setProposals(saved);
      const source: PendingSource = uploaded ?? {
        raw_text: sampleCareerSource,
        source_type: "RESUME",
        label: "Sprint 5 sample resume",
      };
      try {
        const ingestion = await submitListeningSource(source);
        const sourceIds = rememberListeningSource(ingestion.source.id);
        const result = await generateListeningProposals(sourceIds);
        if (!cancelled) addProposals(result.proposals);
      } catch (reason) {
        if (!cancelled) {
          setError(
            reason instanceof Error
              ? reason.message
              : "The listening engine is unavailable.",
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
    setIsLoading(true);
    setListeningStep(0);
    try {
      const ingestion = await submitListeningSource({
        raw_text: message,
        source_type: "CONVERSATION",
        label: "Guided Story conversation",
      });
      const sourceIds = rememberListeningSource(ingestion.source.id);
      const result = await generateListeningProposals(sourceIds);
      addProposals(result.proposals);
      const clarification = result.proposals.find(
        (proposal) => proposal.clarification,
      )?.clarification;
      if (clarification) return clarification.question;
      return result.proposals.length
        ? `I found ${result.proposals.length} explainable proposal${result.proposals.length === 1 ? "" : "s"}. Review the source evidence beside our conversation.`
        : "I didn’t find a complete career entity in that message. Try naming the experience, project, skill, or achievement you want to capture.";
    } finally {
      setIsLoading(false);
    }
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
            <div
              aria-live="polite"
              className="mt-2 flex items-center gap-2 text-xs font-medium text-[#4e7a68]"
            >
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#55a47f] opacity-40" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-[#4a9b76]" />
              </span>
              {listeningStages[listeningStep]}
            </div>
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
