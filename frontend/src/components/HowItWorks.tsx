const steps = [
  {
    step: "01",
    title: "Add your profile",
    description: "Share your resume, skills, and the roles or companies you are targeting.",
  },
  {
    step: "02",
    title: "AI finds your gaps",
    description: "We compare you against the requirements and rank what is missing by impact.",
  },
  {
    step: "03",
    title: "Follow your roadmap",
    description: "Work through a personalized plan and watch your readiness score climb.",
  },
];

export default function HowItWorks() {
  return (
    <section id="how" className="border-y border-white/5 bg-white/[0.02]">
      <div className="mx-auto max-w-6xl px-6 py-24">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            How PrepPilot works
          </h2>
          <p className="mt-4 text-slate-400">Three steps from “I don’t know where to start” to a plan.</p>
        </div>

        <ol className="mt-14 grid gap-6 md:grid-cols-3">
          {steps.map((item) => (
            <li
              key={item.step}
              className="rounded-2xl border border-white/5 bg-slate-950/40 p-6"
            >
              <span className="text-sm font-bold text-indigo-400">{item.step}</span>
              <h3 className="mt-3 text-lg font-semibold text-white">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">{item.description}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
