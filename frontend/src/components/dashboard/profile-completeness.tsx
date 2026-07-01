export function ProfileCompleteness() {
  return (
    <section className="relative overflow-hidden rounded-[26px] bg-[#173f35] p-6 text-white shadow-[0_25px_60px_-38px_rgba(23,63,53,0.9)] sm:p-7">
      <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-[#3b8065] opacity-30 blur-2xl" />
      <div className="relative">
        <p className="text-[10px] font-bold uppercase tracking-[0.17em] text-[#b8d7c9]">
          Profile completeness
        </p>
        <div className="mt-5 flex items-end justify-between gap-4">
          <div>
            <p className="text-5xl font-semibold tracking-[-0.05em]">78%</p>
            <p className="mt-2 max-w-sm text-sm leading-6 text-[#bdd2c8]">
              A strong start. Confirm two details and add leadership evidence to
              make your profile more useful.
            </p>
          </div>
          <div className="relative grid h-24 w-24 shrink-0 place-items-center rounded-full bg-[conic-gradient(#a7d8bd_0_78%,rgba(255,255,255,0.12)_78%_100%)]">
            <span className="grid h-16 w-16 place-items-center rounded-full bg-[#173f35] text-xs font-bold text-[#d9eee3]">
              Strong
            </span>
          </div>
        </div>
        <div className="mt-6 h-2 overflow-hidden rounded-full bg-white/10">
          <div className="h-full w-[78%] rounded-full bg-[#a7d8bd]" />
        </div>
      </div>
    </section>
  );
}
