import Link from "next/link";

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link
      className="inline-flex items-center gap-3 text-[#12241f]"
      href="/"
      aria-label="CareerOS home"
    >
      <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#173f35] text-sm font-bold text-[#f7f2e8] shadow-sm">
        CO
      </span>
      {!compact && (
        <span>
          <span className="block text-[17px] font-semibold tracking-[-0.02em]">
            CareerOS
          </span>
          <span className="block text-[10px] font-semibold uppercase tracking-[0.18em] text-[#668078]">
            Your professional memory
          </span>
        </span>
      )}
    </Link>
  );
}
