const features = [
  {
    title: "Skill Gap Analysis",
    description:
      "Compare your current skills against target role requirements and see exactly what is missing.",
    path: "M4 19V5m0 14h16M8 15l3-4 3 3 5-7",
  },
  {
    title: "AI Mock Interviews",
    description:
      "Practice role-specific questions with an AI interviewer and get instant, actionable feedback.",
    path: "M8 10h8M8 14h5M21 12a8 8 0 0 1-11.3 7.1L4 21l1.9-5.7A8 8 0 1 1 21 12z",
  },
  {
    title: "Smart Roadmap",
    description:
      "Get a week-by-week study plan ordered by impact, so you focus on what moves the needle.",
    path: "M4 6h16M4 12h10M4 18h7",
  },
  {
    title: "Resume Insights",
    description:
      "Turn your resume into structured skills and spot the keywords recruiters actually look for.",
    path: "M7 3h7l4 4v14H7zM14 3v4h4",
  },
  {
    title: "Progress Analytics",
    description:
      "Track readiness over time with clear metrics that show how close you are to interview-ready.",
    path: "M5 21V10M12 21V4M19 21v-7",
  },
  {
    title: "Company Tracks",
    description:
      "Follow preparation paths tailored to the specific companies and roles you are targeting.",
    path: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 4a6 6 0 1 0 0 12 6 6 0 0 0 0-12zm0 4a2 2 0 1 0 0 4 2 2 0 0 0 0-4z",
  },
];

export default function Features() {
  return (
    <section id="features" className="mx-auto max-w-6xl px-6 py-24">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
          Everything you need to prepare smarter
        </h2>
        <p className="mt-4 text-slate-400">
          One workspace that turns a vague goal — “get placed” — into a clear, measurable plan.
        </p>
      </div>

      <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {features.map((feature) => (
          <article
            key={feature.title}
            className="group rounded-2xl border border-white/5 bg-white/[0.03] p-6 transition hover:border-indigo-400/30 hover:bg-white/[0.05]"
          >
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-linear-to-br from-indigo-500/20 to-fuchsia-500/20 text-indigo-300 ring-1 ring-white/10">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.7}
                strokeLinecap="round"
                strokeLinejoin="round"
                className="h-5 w-5"
                aria-hidden
              >
                <path d={feature.path} />
              </svg>
            </span>
            <h3 className="mt-5 text-lg font-semibold text-white">{feature.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-400">{feature.description}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
