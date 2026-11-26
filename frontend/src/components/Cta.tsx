import { DOCS_URL } from "../lib/api";

export default function Cta() {
  return (
    <section id="waitlist" className="mx-auto max-w-6xl px-6 pb-24">
      <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-linear-to-br from-indigo-600/20 via-violet-600/10 to-fuchsia-600/20 px-8 py-14 text-center">
        <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute left-1/2 top-0 h-64 w-[600px] -translate-x-1/2 rounded-full bg-fuchsia-500/20 blur-[100px]" />
        </div>
        <h2 className="mx-auto max-w-2xl text-3xl font-bold tracking-tight text-white sm:text-4xl">
          Be first to prepare with PrepPilot
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-slate-300">
          Authentication and AI features arrive in the next phases. Follow along as the platform comes to life.
        </p>
        <a
          href={DOCS_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-8 inline-block rounded-xl bg-white px-6 py-3 text-sm font-semibold text-slate-900 transition hover:bg-slate-200"
        >
          Explore the live API
        </a>
      </div>
    </section>
  );
}
