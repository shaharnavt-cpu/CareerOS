import { dashboardSummary } from "@/lib/onboarding-data";

const strengthStyles: Record<string, string> = {
  Strong: "bg-[#e5f4eb] text-[#2c694f]",
  Good: "bg-[#eaf3f7] text-[#35697e]",
  Review: "bg-[#fff3da] text-[#8a5b16]",
};

export function KnowledgeSummary() {
  return (
    <section className="rounded-[26px] border border-[#dce4df] bg-white p-5 shadow-[0_20px_50px_-42px_rgba(20,58,46,0.7)] sm:p-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7d8e87]">
            Knowledge overview
          </p>
          <h2 className="mt-1 text-xl font-semibold tracking-[-0.02em] text-[#17362d]">
            Your career, organized
          </h2>
        </div>
        <span className="text-xs font-semibold text-[#668078]">7 items</span>
      </div>
      <div className="mt-5 grid gap-2 sm:grid-cols-2">
        {dashboardSummary.map((item) => (
          <div
            className="flex items-center justify-between rounded-2xl border border-[#e4e9e5] bg-[#fafbf9] px-4 py-3"
            key={item.label}
          >
            <div>
              <p className="text-sm font-semibold text-[#29463c]">{item.label}</p>
              <p className="mt-0.5 text-xs text-[#8a9893]">
                {item.count} {item.count === 1 ? "item" : "items"}
              </p>
            </div>
            <span
              className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.08em] ${strengthStyles[item.strength]}`}
            >
              {item.strength}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
