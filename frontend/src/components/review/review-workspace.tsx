"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { StatusBadge } from "@/components/common/status-badge";
import { categoryOrder } from "@/lib/onboarding-data";
import { evidenceCategoryLabel } from "@/lib/listening-utils";
import {
  clarificationReasonLabel,
  editReviewProposal,
  listReviewProposals,
  loadProposals,
  loadReviewSummary,
  type KnowledgeProposal,
  proposalCategory,
  proposalDetail,
  proposalPrimaryField,
  proposalStructuredFields,
  proposalTitle,
  reviewKnowledgeProposal,
  saveProposals,
} from "@/lib/knowledge-api";

export function ReviewWorkspace() {
  const [items, setItems] = useState<KnowledgeProposal[]>([]);
  const [summary, setSummary] = useState(loadReviewSummary());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [notice, setNotice] = useState(
    "Nothing becomes canonical until you approve it.",
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSummary(loadReviewSummary());
      listReviewProposals()
        .then((proposals) => {
          setItems(proposals);
          saveProposals(proposals);
        })
        .catch(() => setItems(loadProposals()));
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const reviewedCount = useMemo(
    () =>
      items.filter((item) => item.approval_state !== "NEEDS_REVIEW").length,
    [items],
  );

  function updateItem(updated: KnowledgeProposal) {
    setItems((current) => {
      const next = current.map((item) =>
        item.id === updated.id ? updated : item,
      );
      saveProposals(next);
      return next;
    });
  }

  async function decide(
    proposal: KnowledgeProposal,
    decision: "APPROVE" | "REJECT",
  ) {
    setPendingId(proposal.id);
    try {
      const result = await reviewKnowledgeProposal(proposal, decision);
      updateItem(result.proposal);
      setNotice(
        decision === "APPROVE"
          ? "Approved and saved to Career Memory with its evidence."
          : "Rejected. This proposal was not written to Career Memory.",
      );
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "CareerOS could not apply that decision.",
      );
    } finally {
      setPendingId(null);
    }
  }

  function startEditing(item: KnowledgeProposal) {
    setEditingId(item.id);
    setDraftTitle(proposalTitle(item));
  }

  async function saveEdit(item: KnowledgeProposal) {
    const value = draftTitle.trim();
    if (!value) return;
    const primaryField = proposalPrimaryField(item);
    const edited = {
      ...item,
      proposed_value: {
        ...item.proposed_value,
        [primaryField]: value,
        ...(item.entity_type === "SKILL"
          ? { normalized_name: value.toLowerCase() }
          : {}),
      },
      clarification: null,
      approval_state: "NEEDS_REVIEW",
    } satisfies KnowledgeProposal;
    setPendingId(item.id);
    try {
      const saved = await editReviewProposal(edited);
      updateItem(saved);
      setEditingId(null);
      setNotice("Edit saved. Approve it to update Career Memory.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Edit could not be saved.");
    } finally {
      setPendingId(null);
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-5 py-10 sm:px-8 lg:py-14">
      <div className="flex flex-col justify-between gap-6 border-b border-[#dbe3de] pb-8 md:flex-row md:items-end">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-[#3e7d62]">
            Your review
          </p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.045em] text-[#142f26] sm:text-5xl">
            Review your career memories.
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-[#667871]">
            CareerOS grouped {summary.evidence_count} saved evidence points into{" "}
            {items.length} meaningful proposals. Supporting details stay available
            without crowding the queue.
          </p>
        </div>
        <div className="rounded-2xl border border-[#d6e3db] bg-white px-5 py-4 shadow-sm">
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#84928d]">
            Review progress
          </p>
          <p className="mt-1 text-2xl font-semibold text-[#265a48]">
            {reviewedCount}
            <span className="text-sm font-medium text-[#8a9993]">
              /{items.length}
            </span>
          </p>
          <p className="mt-1 text-[10px] text-[#84928d]">
            {summary.hidden_supporting_evidence_count} supporting evidence points
            saved quietly
          </p>
        </div>
      </div>

      <div
        aria-live="polite"
        className="mt-6 rounded-2xl border border-[#cfe1d7] bg-[#edf7f1] px-4 py-3 text-sm text-[#3d6c59]"
      >
        {notice}
      </div>

      {items.length === 0 ? (
        <div className="mt-8 rounded-[22px] border border-dashed border-[#cfdad3] bg-white p-8 text-center">
          <p className="text-sm text-[#65766f]">No proposals are ready yet.</p>
          <Link
            className="mt-4 inline-flex rounded-full bg-[#173f35] px-5 py-2.5 text-sm font-semibold text-white"
            href="/onboarding"
          >
            Analyze a career source
          </Link>
        </div>
      ) : (
        <div className="mt-8 space-y-10">
          {categoryOrder.map((category) => {
            const categoryItems = items.filter(
              (item) => proposalCategory(item) === category,
            );

            return (
              <section key={category}>
                <div className="mb-3 flex items-center gap-3">
                  <h2 className="text-sm font-bold uppercase tracking-[0.13em] text-[#49635a]">
                    {category}
                  </h2>
                  <span className="h-px flex-1 bg-[#dce4df]" />
                  <span className="text-xs text-[#8d9a95]">
                    {categoryItems.length}
                  </span>
                </div>
                <div className="grid gap-3 lg:grid-cols-2">
                  {categoryItems.map((item) => (
                    <article
                      className={`rounded-[22px] border bg-white p-5 shadow-[0_14px_35px_-30px_rgba(23,63,53,0.75)] transition ${
                        item.approval_state === "CANONICAL"
                          ? "border-[#91c8ab] ring-2 ring-[#dff1e7]"
                          : item.approval_state === "REJECTED"
                            ? "border-[#e4d6d1] opacity-55"
                            : "border-[#dce4df]"
                      }`}
                      key={item.id}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          {editingId === item.id ? (
                            <div className="flex gap-2">
                              <input
                                aria-label={`Edit ${proposalTitle(item)}`}
                                autoFocus
                                className="min-w-0 flex-1 rounded-xl border border-[#a9c7b8] px-3 py-2 text-sm text-[#1c3b31] outline-none ring-[#dceee5] focus:ring-4"
                                onChange={(event) =>
                                  setDraftTitle(event.target.value)
                                }
                                value={draftTitle}
                              />
                              <button
                                className="rounded-xl bg-[#245f4d] px-3 text-xs font-semibold text-white"
                                onClick={() => void saveEdit(item)}
                                type="button"
                              >
                                Save
                              </button>
                            </div>
                          ) : (
                            <h3 className="text-base font-semibold text-[#19372e]">
                              {proposalTitle(item)}
                            </h3>
                          )}
                          <p className="mt-1.5 text-sm leading-6 text-[#6a7b74]">
                            {proposalDetail(item)}
                          </p>
                          <p className="mt-2 text-[10px] font-bold uppercase tracking-[0.1em] text-[#4d7967]">
                            {(item.proposal_type ?? item.entity_type).replaceAll("_", " ")}
                            {item.review_status
                              ? ` · ${item.review_status.replaceAll("_", " ")}`
                              : ""}
                          </p>
                        </div>
                        <StatusBadge status={item.approval_state} />
                      </div>

                      <div className="mt-4 grid gap-2 rounded-2xl bg-[#f7f9f6] p-3 text-xs leading-5 text-[#60736b]">
                        <dl className="grid gap-2 rounded-xl border border-[#e0e8e3] bg-white p-3 sm:grid-cols-2">
                          {proposalStructuredFields(item).map((field) => (
                            <div key={field.label}>
                              <dt className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#7b8d85]">
                                {field.label}
                              </dt>
                              <dd className="mt-0.5 text-xs text-[#29483e]">
                                {field.value}
                              </dd>
                            </div>
                          ))}
                        </dl>
                        <p>
                          <span className="font-semibold text-[#36594b]">
                            Confidence:
                          </span>{" "}
                          {Math.round(item.confidence * 100)}%
                        </p>
                        <p>
                          <span className="font-semibold text-[#36594b]">
                            Evidence:
                          </span>{" "}
                          {item.evidence.map((evidence) => evidence.excerpt).join(" · ")}
                        </p>
                        <div className="mt-1 space-y-2">
                          {item.evidence.slice(0, 3).map((evidence, index) => (
                            <div
                              className="rounded-xl border border-[#dfe8e2] bg-white p-3"
                              key={
                                evidence.evidence_id ??
                                `${evidence.source_id}-${index}`
                              }
                            >
                              <div className="flex flex-wrap items-center gap-1.5">
                                <span className="font-semibold text-[#2f5d4d]">
                                  {evidence.title}
                                </span>
                                <span className="rounded-full bg-[#edf4f0] px-2 py-0.5 text-[9px] font-bold uppercase tracking-[0.08em] text-[#5b756a]">
                                  {evidenceCategoryLabel(evidence)}
                                </span>
                                {evidence.corroborated && (
                                  <span className="rounded-full bg-[#e1f2e8] px-2 py-0.5 text-[9px] font-bold uppercase tracking-[0.08em] text-[#337057]">
                                    Corroborated
                                  </span>
                                )}
                              </div>
                              <blockquote className="mt-1.5 border-l-2 border-[#a9cbbb] pl-2.5 text-[#526860]">
                                “{evidence.excerpt}”
                              </blockquote>
                              <p className="mt-1 text-[10px] text-[#7b8d86]">
                                {evidence.source_type.replaceAll("_", " ")}
                                {evidence.location
                                  ? ` · ${evidence.location}`
                                  : ""}
                                {evidence.confidence != null
                                  ? ` · ${Math.round(evidence.confidence * 100)}% extraction confidence`
                                  : ""}
                              </p>
                            </div>
                          ))}
                          {item.evidence.length > 3 && (
                            <details className="rounded-xl border border-[#dfe8e2] bg-white p-3">
                              <summary className="cursor-pointer font-semibold text-[#426657]">
                                Show {item.evidence.length - 3} more evidence references
                              </summary>
                              <div className="mt-2 space-y-2">
                                {item.evidence.slice(3).map((evidence, index) => (
                                  <blockquote
                                    className="border-l-2 border-[#a9cbbb] pl-2.5 text-[#526860]"
                                    key={evidence.evidence_id ?? index}
                                  >
                                    “{evidence.excerpt}”
                                  </blockquote>
                                ))}
                              </div>
                            </details>
                          )}
                        </div>
                        <p>
                          <span className="font-semibold text-[#36594b]">
                            Reasoning:
                          </span>{" "}
                          {item.reasoning_summary}
                        </p>
                        {item.clarification && (
                          <div className="rounded-xl border border-[#ead6a9] bg-[#fff7e5] p-3 text-[#76541f]">
                            <p className="font-semibold">
                              {clarificationReasonLabel(item.clarification.reason)}
                            </p>
                            <p>{item.clarification.detail}</p>
                            <p className="mt-1 font-medium">
                              {item.clarification.question}
                            </p>
                          </div>
                        )}
                      </div>

                      <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-[#edf0ed] pt-4">
                        <button
                          className="rounded-full bg-[#e4f3ea] px-3.5 py-2 text-xs font-semibold text-[#2c684f] transition hover:bg-[#cfe9da] disabled:cursor-not-allowed disabled:opacity-45"
                          disabled={
                            pendingId === item.id ||
                            item.approval_state === "CANONICAL" ||
                            Boolean(item.clarification)
                          }
                          onClick={() => void decide(item, "APPROVE")}
                          title={
                            item.clarification
                              ? "Edit the proposal to resolve its clarification first."
                              : undefined
                          }
                          type="button"
                        >
                          {pendingId === item.id ? "Saving…" : "Approve"}
                        </button>
                        <button
                          className="rounded-full border border-[#d7e1db] px-3.5 py-2 text-xs font-semibold text-[#566b63] transition hover:bg-[#f2f6f3]"
                          onClick={() => startEditing(item)}
                          type="button"
                        >
                          Edit
                        </button>
                        <button
                          className="rounded-full px-3.5 py-2 text-xs font-semibold text-[#9a5c4e] transition hover:bg-[#fbefeb] disabled:opacity-45"
                          disabled={pendingId === item.id}
                          onClick={() => void decide(item, "REJECT")}
                          type="button"
                        >
                          Reject
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}

      <div className="mt-12 flex flex-col items-center justify-between gap-4 rounded-[24px] bg-[#173f35] p-5 text-white sm:flex-row sm:p-6">
        <div>
          <p className="font-semibold">Ready to see the shape of your profile?</p>
          <p className="mt-1 text-sm text-[#bdd6ca]">
            You can keep refining it at any time.
          </p>
        </div>
        <Link
          className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-full bg-[#f5f2e8] px-5 text-sm font-semibold text-[#173f35] transition hover:bg-white sm:w-auto"
          href="/dashboard"
        >
          Continue to Dashboard
          <span aria-hidden="true">→</span>
        </Link>
      </div>
    </main>
  );
}
