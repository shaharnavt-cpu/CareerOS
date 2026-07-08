"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { ChatPanel } from "@/components/chat/chat-panel";
import { KnowledgePanel } from "@/components/knowledge/knowledge-panel";
import { SourceListeningPanel } from "@/components/onboarding/source-listening-panel";
import {
  friendlyFailureMessage,
  mergeById,
  validateListeningAttachments,
} from "@/lib/listening-utils";
import {
  CareerOSApiError,
  generateListeningProposals,
  listListeningJobs,
  loadProposals,
  type KnowledgeProposal,
  type ListeningJob,
  rememberListeningSource,
  replacePendingProposals,
  retryListeningJob,
  saveProposals,
  submitListeningSource,
  uploadListeningFiles,
} from "@/lib/knowledge-api";

function errorMessage(reason: unknown, fallback: string) {
  if (reason instanceof CareerOSApiError) {
    return friendlyFailureMessage(reason.code) || reason.message;
  }
  return reason instanceof Error ? reason.message : fallback;
}

export function OnboardingWorkspace() {
  const [proposals, setProposals] = useState<KnowledgeProposal[]>([]);
  const [jobs, setJobs] = useState<ListeningJob[]>([]);
  const [conversationError, setConversationError] = useState<string | null>(
    null,
  );
  const [sourceError, setSourceError] = useState<string | null>(null);
  const initialized = useRef(false);
  const processedJobs = useRef(new Set<string>());
  const hiddenJobs = useRef(new Set<string>());

  const addProposals = useCallback((incoming: KnowledgeProposal[]) => {
    setProposals((current) => {
      const next = replacePendingProposals(current, incoming);
      saveProposals(next);
      return next;
    });
  }, []);

  const processCompletedJobs = useCallback(
    (incoming: ListeningJob[]) => {
      const completed = incoming.filter(
        (job) =>
          job.status === "COMPLETE" &&
          job.source_id &&
          !processedJobs.current.has(job.id),
      );
      if (!completed.length) return;

      completed.forEach((job) => processedJobs.current.add(job.id));
      completed.forEach((job) => {
        if (job.source_id) rememberListeningSource(job.source_id);
      });
      addProposals(completed.flatMap((job) => job.proposals));
    },
    [addProposals],
  );

  const synchronizeJobs = useCallback(
    (incoming: ListeningJob[]) => {
      setJobs(incoming.filter((job) => !hiddenJobs.current.has(job.id)));
      processCompletedJobs(incoming);
    },
    [processCompletedJobs],
  );

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    setProposals(loadProposals());
    listListeningJobs()
      .then(synchronizeJobs)
      .catch(() => {
        setSourceError(
          "Source history is temporarily unavailable. You can still keep talking.",
        );
      });
  }, [synchronizeJobs]);

  const hasActiveJobs = jobs.some(
    (job) => job.status === "QUEUED" || job.status === "ACTIVE",
  );
  useEffect(() => {
    if (!hasActiveJobs) return;
    const timeout = window.setTimeout(() => {
      listListeningJobs()
        .then(synchronizeJobs)
        .catch(() => {
          setSourceError(
            "Progress paused for a moment. CareerOS is still listening in the background.",
          );
        });
    }, 700);
    return () => window.clearTimeout(timeout);
  }, [hasActiveJobs, jobs, synchronizeJobs]);

  async function attachSources(files: File[]) {
    setSourceError(null);
    const validation = validateListeningAttachments(files);
    if (validation) {
      setSourceError(validation);
      return;
    }
    try {
      const response = await uploadListeningFiles(files);
      setJobs((current) => mergeById(response.jobs, current));
      processCompletedJobs(response.jobs);
    } catch (reason) {
      setSourceError(errorMessage(reason, "CareerOS could not queue those documents."));
    }
  }

  async function retrySource(jobId: string) {
    setSourceError(null);
    try {
      const retried = await retryListeningJob(jobId);
      processedJobs.current.delete(jobId);
      setJobs((current) => mergeById(current, [retried]));
    } catch (reason) {
      setSourceError(errorMessage(reason, "CareerOS could not retry that source."));
    }
  }

  async function reasonAboutConversation(message: string) {
    setConversationError(null);
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
        ? `I found ${result.proposals.length} explainable proposal${result.proposals.length === 1 ? "" : "s"}. You can review the source evidence beside our conversation.`
        : "I didn’t find a complete career entity in that message. Try naming the experience, project, skill, or achievement you want to capture.";
    } catch (reason) {
      const message =
        reason instanceof Error
          ? reason.message
          : "The listening engine is unavailable.";
      setConversationError(message);
      throw new Error(message);
    }
  }

  return (
    <main className="mx-auto max-w-[1500px] px-4 py-5 sm:px-6 lg:px-8">
      <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#488069]">
            Conversation + evidence
          </p>
          <p className="mt-1 text-sm text-[#70817a]">
            Speak naturally or attach what you already have. CareerOS listens to
            both.
          </p>
          {(sourceError || conversationError) && (
            <p
              aria-live="polite"
              className="mt-1 text-xs font-medium text-[#9a5c4e]"
            >
              {sourceError ?? conversationError}
            </p>
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
        <ChatPanel onAttach={attachSources} onReason={reasonAboutConversation} />
        <div className="space-y-4">
          <SourceListeningPanel
            jobs={jobs}
            onDismiss={(jobId) => {
              hiddenJobs.current.add(jobId);
              setJobs((current) => current.filter((job) => job.id !== jobId));
            }}
            onRetry={retrySource}
          />
          <KnowledgePanel
            items={proposals}
            stage={Math.min(3, Math.max(1, Math.ceil(proposals.length / 2)))}
          />
        </div>
      </div>
    </main>
  );
}
