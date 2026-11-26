import { useEffect, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import TagList from "../components/TagList";
import { getApiErrorMessage, getJob, type JobDetail } from "../lib/api";
import { formatDate } from "../lib/format";

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function BulletList({ items, emptyText }: { items: string[]; emptyText?: string }) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">{emptyText ?? "None detected"}</p>;
  }
  return (
    <ul className="space-y-2">
      {items.map((item, index) => (
        <li key={`${item}-${index}`} className="flex gap-2 text-sm text-slate-300">
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-400" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();

  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const numericId = Number(id);
    if (!Number.isInteger(numericId) || numericId <= 0) {
      setError("Invalid job id.");
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    getJob(numericId)
      .then((data) => {
        if (active) setJob(data);
      })
      .catch((err) => {
        if (active) setError(getApiErrorMessage(err));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [id]);

  return (
    <div className="min-h-screen bg-slate-950 font-sans text-slate-100">
      <Navbar />
      <main className="mx-auto max-w-5xl px-6 py-12">
        <Link
          to="/jobs"
          className="text-sm font-medium text-indigo-300 transition hover:text-indigo-200"
        >
          ← Back to job descriptions
        </Link>

        {loading ? (
          <p className="mt-6 animate-pulse text-sm text-slate-400">Loading analysis…</p>
        ) : error ? (
          <p className="mt-6 rounded-lg border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </p>
        ) : job ? (
          <>
            <header className="mt-4 flex flex-wrap items-end justify-between gap-4">
              <div className="min-w-0">
                <h1 className="truncate text-3xl font-bold tracking-tight text-white">
                  {job.job_title}
                </h1>
                <p className="mt-1 text-slate-400">Analyzed {formatDate(job.created_at)}</p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <Link
                  to={`/analysis/new?jobId=${job.id}`}
                  className="rounded-lg bg-linear-to-r from-indigo-500 to-fuchsia-500 px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
                >
                  Match resume →
                </Link>
                <span className="rounded-full border border-indigo-400/20 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-200">
                  {job.analysis_engine === "llm" ? "AI analysis" : "Heuristic preview"}
                </span>
              </div>
            </header>

            {job.analysis_engine !== "llm" && (
              <p className="mt-4 rounded-lg border border-amber-400/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
                AI is not configured on this server, so this result came from the
                rule-based fallback. Set <code className="font-mono">LLM_API_KEY</code> to
                enable AI extraction.
              </p>
            )}

            <div className="mt-8 grid gap-6 lg:grid-cols-2">
              <Panel title="Required skills">
                <TagList items={job.required_skills} />
              </Panel>
              <Panel title="Preferred skills">
                <TagList items={job.preferred_skills} emptyText="None listed" />
              </Panel>

              <Panel title="Programming languages">
                <TagList items={job.programming_languages} />
              </Panel>
              <Panel title="Frameworks & libraries">
                <TagList items={job.frameworks} />
              </Panel>
              <Panel title="Databases">
                <TagList items={job.databases} />
              </Panel>
              <Panel title="Cloud technologies">
                <TagList items={job.cloud_technologies} />
              </Panel>
              <Panel title="Tools">
                <TagList items={job.tools} />
              </Panel>
              <Panel title="Soft skills">
                <TagList items={job.soft_skills} />
              </Panel>

              <Panel title="Experience requirements">
                <BulletList items={job.experience_requirements} />
              </Panel>
              <Panel title="Education requirements">
                <BulletList items={job.education_requirements} />
              </Panel>
            </div>

            <details className="mt-6 rounded-2xl border border-white/10 bg-white/[0.03] p-6">
              <summary className="cursor-pointer text-sm font-semibold text-slate-300">
                Original job description
              </summary>
              <pre className="mt-4 max-h-80 overflow-auto whitespace-pre-wrap text-xs leading-relaxed text-slate-400">
                {job.original_text}
              </pre>
            </details>
          </>
        ) : null}
      </main>
      <Footer />
    </div>
  );
}
