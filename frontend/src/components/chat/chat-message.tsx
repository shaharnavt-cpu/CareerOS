import type { ChatMessage as ChatMessageType } from "@/lib/onboarding-data";

export function ChatMessage({ message }: { message: ChatMessageType }) {
  const isAssistant = message.author === "assistant";

  return (
    <article
      className={`flex gap-3 ${isAssistant ? "justify-start" : "justify-end"}`}
    >
      {isAssistant && (
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-[#173f35] text-[10px] font-bold text-white">
          CO
        </span>
      )}
      <div
        className={`max-w-[82%] ${isAssistant ? "items-start" : "items-end"} flex flex-col`}
      >
        <div
          className={`rounded-[20px] px-4 py-3 text-sm leading-6 shadow-sm ${
            isAssistant
              ? "rounded-tl-md border border-[#dce5df] bg-white text-[#30473f]"
              : "rounded-tr-md bg-[#245f4d] text-white"
          }`}
        >
          {message.body}
        </div>
        <time className="mt-1.5 px-1 text-[10px] font-medium text-[#97a39e]">
          {message.timestamp}
        </time>
      </div>
    </article>
  );
}
