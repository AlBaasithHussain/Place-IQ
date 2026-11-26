import { DOCS_URL } from "../lib/api";
import StatusBadge from "./StatusBadge";

const stats = [
  { value: "40+", label: "Skill areas analyzed" },
  { value: "100%", label: "Personalized roadmap" },
  { value: "Free", label: "Built for students" },
];

export default function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute left-1/2 top-[-10%] h-[420px] w-[720px] -translate-x-1/2 rounded-full bg-indigo-600/30 blur-[120px]" />
        <div className="absolute right-[-10%] top-[20%] h-[320px] w-[320px] rounded-full bg-fuchsia-600/20 blur-[100px]" />
      </div>

      <div className="mx-auto max-w-6xl px-6 pb-24 pt-20 text-center md:pt-28">
        <div className="mb-6 flex justify-center">
          <StatusBadge />
        </div>

        <p className="mb-5 inline-block rounded-full border border-indigo-400/30 bg-indigo-500/10 px-4 py-1 text-xs font-semibold uppercase tracking-widest text-indigo-300">
          Phase 1 · Foundation
        </p>

        <h1 className="mx-auto max-w-4xl text-4xl font-extrabold leading-tight tracking-tight text-white sm:text-6xl">
          Land your dream placement with{" "}
          <span className="bg-linear-to-r from-indigo-400 via-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
            AI-guided preparation
          </span>
        </h1>

        <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-slate-300">
          PrepPilot compares your skills against real job requirements, pinpoints your gaps, and
          builds a personalized study roadmap — so you always know exactly what to work on next.
        </p>

        <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <a
            href="#features"
            className="rounded-xl bg-linear-to-r from-indigo-500 to-fuchsia-500 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-900/40 transition hover:opacity-90"
          >
            Explore features
          </a>
          <a
            href={DOCS_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-xl border border-white/10 bg-white/5 px-6 py-3 text-sm font-semibold text-slate-200 transition hover:bg-white/10"
          >
            View API docs
          </a>
        </div>

        <dl className="mx-auto mt-16 grid max-w-3xl grid-cols-1 gap-4 sm:grid-cols-3">
          {stats.map((stat) => (
            <div
              key={stat.label}
              className="rounded-2xl border border-white/5 bg-white/[0.03] px-6 py-5 backdrop-blur"
            >
              <dt className="text-3xl font-extrabold text-white">{stat.value}</dt>
              <dd className="mt-1 text-sm text-slate-400">{stat.label}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
