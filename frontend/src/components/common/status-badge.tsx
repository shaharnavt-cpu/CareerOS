import type { KnowledgeStatus } from "@/lib/onboarding-data";

const statusStyles: Record<KnowledgeStatus, string> = {
  confirmed: "border-[#b8ddc9] bg-[#e8f6ed] text-[#236442]",
  "needs-review": "border-[#eed5a3] bg-[#fff5dd] text-[#8b5a15]",
  "recently-added": "border-[#b9d9ea] bg-[#eaf6fc] text-[#256582]",
};

const statusLabels: Record<KnowledgeStatus, string> = {
  confirmed: "Confirmed",
  "needs-review": "Needs Review",
  "recently-added": "Recently Added",
};

export function StatusBadge({ status }: { status: KnowledgeStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.08em] ${statusStyles[status]}`}
    >
      {statusLabels[status]}
    </span>
  );
}
