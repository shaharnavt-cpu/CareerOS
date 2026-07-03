"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import { ChatMessage } from "@/components/chat/chat-message";
import {
  initialMessages,
  quickReplies,
  type ChatMessage as ChatMessageType,
} from "@/lib/onboarding-data";

function currentTime() {
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date());
}

export function ChatPanel({
  onReason,
}: {
  onReason: (message: string) => Promise<string>;
}) {
  const [messages, setMessages] = useState<ChatMessageType[]>(initialMessages);
  const [input, setInput] = useState("");
  const [turn, setTurn] = useState(0);
  const [isReplying, setIsReplying] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isReplying]);

  async function submitMessage(value: string) {
    const message = value.trim();
    if (!message || isReplying) return;

    setMessages((current) => [
      ...current,
      {
        id: `user-${crypto.randomUUID()}`,
        author: "user",
        body: message,
        timestamp: currentTime(),
      },
    ]);
    setInput("");
    setIsReplying(true);

    try {
      const reply = await onReason(message);
      setMessages((current) => [
        ...current,
        {
          id: `assistant-${crypto.randomUUID()}`,
          author: "assistant",
          body: reply,
          timestamp: currentTime(),
        },
      ]);
      setTurn((current) => current + 1);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: `assistant-error-${crypto.randomUUID()}`,
          author: "assistant",
          body:
            error instanceof Error
              ? `I couldn’t analyze that yet: ${error.message}`
              : "I couldn’t analyze that yet. Please try again.",
          timestamp: currentTime(),
        },
      ]);
    } finally {
      setIsReplying(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitMessage(input);
  }

  return (
    <section className="flex min-h-[680px] flex-col overflow-hidden rounded-[26px] border border-[#d9e3dc] bg-[#f3f6f2] shadow-[0_24px_70px_-48px_rgba(20,58,46,0.65)] lg:h-[calc(100vh-7.5rem)] lg:min-h-0">
      <div className="flex items-center justify-between gap-4 border-b border-[#dde5df] bg-white/85 px-5 py-4 backdrop-blur">
        <div className="flex items-center gap-3">
          <span className="relative grid h-10 w-10 place-items-center rounded-2xl bg-[#173f35] text-xs font-bold text-white">
            CO
            <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-white bg-[#54a77e]" />
          </span>
          <div>
            <h1 className="text-sm font-semibold text-[#1a392f]">Guided Story</h1>
            <p className="text-xs text-[#7b8c86]">
              Your thoughtful career interviewer
            </p>
          </div>
        </div>
        <span className="rounded-full bg-[#edf5f0] px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.12em] text-[#3f775f]">
          Reasoning active
        </span>
      </div>

      <div
        aria-live="polite"
        className="flex-1 space-y-5 overflow-y-auto px-4 py-6 sm:px-6"
      >
        <div className="mx-auto mb-6 max-w-sm rounded-full border border-[#dce4df] bg-white/65 px-4 py-2 text-center text-[10px] font-semibold uppercase tracking-[0.14em] text-[#83918c]">
          Today · Building your career story
        </div>
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
        {isReplying && (
          <div className="flex items-center gap-3">
            <span className="grid h-8 w-8 place-items-center rounded-xl bg-[#173f35] text-[10px] font-bold text-white">
              CO
            </span>
            <span className="flex items-center gap-2 rounded-2xl rounded-tl-md border border-[#dce5df] bg-white px-4 py-3 text-xs font-medium text-[#658078]">
              Listening to your story
              {[0, 1, 2].map((dot) => (
                <span
                  className="h-1.5 w-1.5 animate-bounce rounded-full bg-[#6d8d80]"
                  key={dot}
                  style={{ animationDelay: `${dot * 120}ms` }}
                />
              ))}
            </span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-[#dce5df] bg-white p-3 sm:p-4">
        <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
          {quickReplies.slice(turn, turn + 2).map((reply) => (
            <button
              className="shrink-0 rounded-full border border-[#d6e2db] bg-[#f9fbf8] px-3 py-2 text-xs font-medium text-[#526a61] transition hover:border-[#92b9a8] hover:bg-[#edf7f1] disabled:opacity-50"
              disabled={isReplying}
              key={reply}
              onClick={() => void submitMessage(reply)}
              type="button"
            >
              {reply}
            </button>
          ))}
        </div>
        <form className="flex items-end gap-2" onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="guided-story-input">
            Tell CareerOS about your story
          </label>
          <textarea
            className="min-h-12 flex-1 resize-none rounded-2xl border border-[#d5dfd9] bg-[#fbfcfa] px-4 py-3 text-sm leading-6 text-[#243f36] outline-none transition placeholder:text-[#9ba7a2] focus:border-[#5a947b] focus:ring-4 focus:ring-[#dceee5]"
            disabled={isReplying}
            id="guided-story-input"
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void submitMessage(input);
              }
            }}
            placeholder="Tell me what you did, what mattered, or what feels hard to classify…"
            rows={1}
            value={input}
          />
          <button
            aria-label="Send message"
            className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-[#173f35] text-white shadow-sm transition hover:bg-[#245b4b] disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!input.trim() || isReplying}
            type="submit"
          >
            <svg
              aria-hidden="true"
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              viewBox="0 0 24 24"
            >
              <path
                d="M4 4l16 8-16 8 3-8-3-8zM7 12h13"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </form>
        <p className="mt-2 text-center text-[10px] text-[#9aa6a1]">
          AI proposes · deterministic checks validate · you approve
        </p>
      </div>
    </section>
  );
}
