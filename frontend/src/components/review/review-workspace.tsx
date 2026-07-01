"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { StatusBadge } from "@/components/common/status-badge";
import {
  categoryOrder,
  knowledgeItems,
  type KnowledgeItem,
} from "@/lib/onboarding-data";

type Decision = "pending" | "approved" | "rejected";
type ReviewItem = KnowledgeItem & { decision: Decision };

export function ReviewWorkspace() {
  const [items, setItems] = useState<ReviewItem[]>(
    knowledgeItems.map((item) => ({ ...item, decision: "pending" })),
  );
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [notice, setNotice] = useState(
    "Nothing becomes canonical until you approve it.",
  );

  const approvedCount = useMemo(
    () => items.filter((item) => item.decision === "approved").length,
    [items],
  );

  function decide(id: string, decision: Decision) {
    setItems((current) =>
      current.map((item) => (item.id === id ? { ...item, decision } : item)),
    );
    setNotice(
      decision === "approved"
        ? "Approved in this preview. No data has been saved."
        : "Rejected in this preview. You can change your decision anytime.",
    );
  }

  function startEditing(item: ReviewItem) {
    setEditingId(item.id);
    setDraftTitle(item.title);
  }

  function saveEdit(id: string) {
    const value = draftTitle.trim();
    if (!value) return;
    setItems((current) =>
      current.map((item) =>
        item.id === id
          ? { ...item, title: value, status: "recently-added" }
          : item,
      ),
    );
    setEditingId(null);
    setNotice("Edit applied locally. No data has been saved.");
  }

  return (
    <main className="mx-auto max-w-6xl px-5 py-10 sm:px-8 lg:py-14">
      <div className="flex flex-col justify-between gap-6 border-b border-[#dbe3de] pb-8 md:flex-row md:items-end">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-[#3e7d62]">
            Your review
          </p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.045em] text-[#142f26] sm:text-5xl">
            Here’s what I understood.
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-[#667871]">
            Check the proposed structure, correct anything that feels off, and
            decide what belongs in your profile. This preview never persists
            your choices.
          </p>
        </div>
        <div className="rounded-2xl border border-[#d6e3db] bg-white px-5 py-4 shadow-sm">
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#84928d]">
            Mock approvals
          </p>
          <p className="mt-1 text-2xl font-semibold text-[#265a48]">
            {approvedCount}
            <span className="text-sm font-medium text-[#8a9993]">
              /{items.length}
            </span>
          </p>
        </div>
      </div>

      <div
        aria-live="polite"
        className="mt-6 rounded-2xl border border-[#cfe1d7] bg-[#edf7f1] px-4 py-3 text-sm text-[#3d6c59]"
      >
        {notice}
      </div>

      <div className="mt-8 space-y-10">
        {categoryOrder.map((category) => {
          const categoryItems = items.filter(
            (item) => item.category === category,
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
                      item.decision === "approved"
                        ? "border-[#91c8ab] ring-2 ring-[#dff1e7]"
                        : item.decision === "rejected"
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
                              aria-label={`Edit ${item.title}`}
                              autoFocus
                              className="min-w-0 flex-1 rounded-xl border border-[#a9c7b8] px-3 py-2 text-sm text-[#1c3b31] outline-none ring-[#dceee5] focus:ring-4"
                              onChange={(event) =>
                                setDraftTitle(event.target.value)
                              }
                              value={draftTitle}
                            />
                            <button
                              className="rounded-xl bg-[#245f4d] px-3 text-xs font-semibold text-white"
                              onClick={() => saveEdit(item.id)}
                              type="button"
                            >
                              Save
                            </button>
                          </div>
                        ) : (
                          <h3 className="text-base font-semibold text-[#19372e]">
                            {item.title}
                          </h3>
                        )}
                        <p className="mt-1.5 text-sm leading-6 text-[#6a7b74]">
                          {item.detail}
                        </p>
                      </div>
                      <StatusBadge status={item.status} />
                    </div>

                    <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-[#edf0ed] pt-4">
                      <button
                        className="rounded-full bg-[#e4f3ea] px-3.5 py-2 text-xs font-semibold text-[#2c684f] transition hover:bg-[#cfe9da]"
                        onClick={() => decide(item.id, "approved")}
                        type="button"
                      >
                        Approve
                      </button>
                      <button
                        className="rounded-full border border-[#d7e1db] px-3.5 py-2 text-xs font-semibold text-[#566b63] transition hover:bg-[#f2f6f3]"
                        onClick={() => startEditing(item)}
                        type="button"
                      >
                        Edit
                      </button>
                      <button
                        className="rounded-full px-3.5 py-2 text-xs font-semibold text-[#9a5c4e] transition hover:bg-[#fbefeb]"
                        onClick={() => decide(item.id, "rejected")}
                        type="button"
                      >
                        Reject
                      </button>
                      {item.decision !== "pending" && (
                        <span className="ml-auto text-[10px] font-bold uppercase tracking-[0.12em] text-[#84928d]">
                          {item.decision}
                        </span>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            </section>
          );
        })}
      </div>

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
