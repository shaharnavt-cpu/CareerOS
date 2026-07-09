export default function Loading() {
  return (
    <main className="grid min-h-screen place-items-center bg-[#f6f7f2] px-5">
      <section className="w-full max-w-xl rounded-[28px] border border-[#dce4df] bg-white p-8 shadow-[0_20px_70px_-45px_rgba(23,63,53,0.85)]">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#3f8064]">
          Loading workspace
        </p>
        <div className="mt-5 space-y-3">
          <div className="h-7 w-3/4 animate-pulse rounded-full bg-[#e7eee9]" />
          <div className="h-4 w-full animate-pulse rounded-full bg-[#edf2ee]" />
          <div className="h-4 w-2/3 animate-pulse rounded-full bg-[#edf2ee]" />
        </div>
      </section>
    </main>
  );
}
