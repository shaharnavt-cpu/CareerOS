import type { ApprovalState } from "@/lib/knowledge-api";

const statusStyles: Record<ApprovalState, string> = {
  DISCOVERED: "border-[#b9d9ea] bg-[#eaf6fc] text-[#256582]",
  NEEDS_REVIEW: "border-[#eed5a3] bg-[#fff5dd] text-[#8b5a15]",
  APPROVED: "border-[#b8ddc9] bg-[#e8f6ed] text-[#236442]",
  REJECTED: "border-[#e4d6d1] bg-[#fbefeb] text-[#9a5c4e]",
  CANONICAL: "border-[#9bcdb3] bg-[#dff1e7] text-[#205c3d]",
};

const statusLabels: Record<ApprovalState, string> = {
  DISCOVERED: "Discovered",
  NEEDS_REVIEW: "Needs Review",
  APPROVED: "Approved",
  REJECTED: "Rejected",
  CANONICAL: "Canonical",
};

export function StatusBadge({ status }: { status: ApprovalState }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.08em] ${statusStyles[status]}`}
    >
      {statusLabels[status]}
    </span>
  );
}
