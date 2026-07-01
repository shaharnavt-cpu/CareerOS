export default function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-slate-100">
      <section className="w-full max-w-2xl rounded-2xl border border-slate-800 bg-slate-900 p-10 shadow-2xl shadow-black/20">
        <p className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-sky-400">
          Sprint 1 · Project Foundation
        </p>
        <h1 className="text-4xl font-semibold tracking-tight">CareerOS</h1>
        <p className="mt-4 max-w-xl text-lg leading-8 text-slate-300">
          The frontend foundation is running. Product capabilities will be
          introduced in future sprints.
        </p>
        <div className="mt-8 inline-flex items-center gap-2 rounded-full border border-emerald-800 bg-emerald-950/60 px-4 py-2 text-sm text-emerald-300">
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
          Frontend ready
        </div>
      </section>
    </main>
  );
}
