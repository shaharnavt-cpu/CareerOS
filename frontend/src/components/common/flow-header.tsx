import { Brand } from "@/components/common/brand";

const steps = ["Welcome", "Conversation", "Review", "Dashboard"];

export function FlowHeader({ current }: { current: number }) {
  return (
    <header className="border-b border-[#dce5df] bg-[#fbfcf8]/90 px-5 py-4 backdrop-blur-xl sm:px-8">
      <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-6">
        <Brand />
        <nav aria-label="Onboarding progress" className="hidden md:block">
          <ol className="flex items-center gap-2">
            {steps.map((step, index) => (
              <li className="flex items-center gap-2" key={step}>
                <span
                  aria-current={index === current ? "step" : undefined}
                  className={`grid h-7 min-w-7 place-items-center rounded-full px-2 text-xs font-semibold transition-colors ${
                    index < current
                      ? "bg-[#173f35] text-white"
                      : index === current
                        ? "bg-[#d9eee4] text-[#173f35] ring-1 ring-[#9bcab5]"
                        : "bg-[#edf1ed] text-[#84918c]"
                  }`}
                >
                  {index < current ? "✓" : index + 1}
                </span>
                <span
                  className={`text-xs font-medium ${index === current ? "text-[#173f35]" : "text-[#7b8984]"}`}
                >
                  {step}
                </span>
                {index < steps.length - 1 && (
                  <span className="mx-1 h-px w-5 bg-[#d5ded8]" />
                )}
              </li>
            ))}
          </ol>
        </nav>
        <span className="rounded-full border border-[#d8e0db] bg-white px-3 py-1.5 text-xs font-medium text-[#52635d] md:hidden">
          Step {current + 1} of 4
        </span>
      </div>
    </header>
  );
}
