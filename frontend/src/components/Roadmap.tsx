const phases = [
  {
    name: "Phase 1 — Foundation",
    status: "Shipped",
    tone: "text-emerald-300 ring-emerald-400/30 bg-emerald-500/10",
    points: ["Full-stack skeleton", "Health API + CORS", "Landing page", "Git + env setup"],
  },
  {
    name: "Phase 2 — Core Data",
    status: "Next",
    tone: "text-indigo-300 ring-indigo-400/30 bg-indigo-500/10",
    points: ["Auth & user profiles", "PostgreSQL models", "Skill taxonomy", "Resume upload"],
  },
  {
    name: "Phase 3 — AI Engine",
    status: "Planned",
    tone: "text-fuchsia-300 ring-fuchsia-400/30 bg-fuchsia-500/10",
    points: ["LLM integration", "Gap analysis", "Roadmap generation", "Mock interviews"],
  },
];

export default function Roadmap() {
  return (
    <section id="roadmap" className="mx-auto max-w-6xl px-6 py-24">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">Product roadmap</h2>
        <p className="mt-4 text-slate-400">
          Phase 1 is the foundation you are looking at right now.
        </p>
      </div>

      <div className="mt-14 grid gap-6 md:grid-cols-3">
        {phases.map((phase) => (
          <article
            key={phase.name}
            className="rounded-2xl border border-white/5 bg-white/[0.03] p-6"
          >
            <span className={`inline-block rounded-full px-3 py-1 text-xs font-semibold ring-1 ${phase.tone}`}>
              {phase.status}
            </span>
            <h3 className="mt-4 text-lg font-semibold text-white">{phase.name}</h3>
            <ul className="mt-4 space-y-2">
              {phase.points.map((point) => (
                <li key={point} className="flex items-start gap-2 text-sm text-slate-400">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-600" />
                  {point}
                </li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </section>
  );
}
