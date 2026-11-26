import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import {
  analyzeJob,
  getApiErrorMessage,
  listJobs,
  type JobSummary,
} from "../lib/api";
import { formatDate } from "../lib/format";

const MIN_LENGTH = 30;
const MAX_LENGTH = 20000;

const SAMPLE_JD = `Senior Python Developer

About the role
We are building data-driven products and need a backend engineer.

Required Skills
Python, SQL, FastAPI, PostgreSQL

Preferred Qualifications
Docker, AWS

You should have 3+ years of experience building backend services.
Bachelor's degree in Computer Science or a related field.
Strong communication and teamwork skills.`;

function engineLabel(engine: string): string {
  return engine === "llm" ? "AI analysis" : "Heuristic preview";
}

export default function JobsPage() {
  const navigate = useNavigate();

  const [text, setText] = useState("");
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    listJobs()
      .then((data) => {
        if (active) setJobs(data);
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
  }, []);

  const trimmedLength = text.trim().length;
  const canAnalyze = trimmedLength >= MIN_LENGTH && trimmedLength <= MAX_LENGTH;

  async function handleAnalyze() {
    if (!canAnalyze) {
      setError(`Paste a job description of at least ${MIN_LENGTH} characters.`);
      return;
    }
    setAnalyzing(true);
    setError(null);
    try {
      const job = await analyzeJob(text.trim());
      navigate(`/jobs/${job.id}`);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 font-sans text-slate-100">
      <Navbar />
      <main className="mx-auto max-w-5xl px-6 py-12">
        <h1 className="text-3xl font-bold tracking-tight text-white">Job descriptions</h1>
        <p className="mt-2 text-slate-400">
          Paste a company&apos;s job description and we&apos;ll extract its requirements.
        </p>

        <section className="mt-8 rounded-2xl border border-white/10 bg-white/[0.03] p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-white">Analyze a job description</h2>
              <p className="mt-1 text-sm text-slate-400">
                We detect required vs preferred skills, technologies and qualifications.
              </p>
            </div>
            <button
              onClick={() => setText(SAMPLE_JD)}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:bg-white/10"
            >
              Try a sample
            </button>
          </div>

          {error && (
            <p className="mt-4 rounded-lg border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
              {error}
            </p>
          )}

          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={12}
            maxLength={MAX_LENGTH}
            placeholder="Paste the full job description here…"
            className="mt-4 w-full resize-y rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2 text-sm leading-relaxed text-white outline-none transition placeholder:text-slate-500 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30"
          />

          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <span className="text-xs text-slate-500">
              {trimmedLength} characters{trimmedLength < MIN_LENGTH ? ` (min ${MIN_LENGTH})` : ""}
            </span>
            <button
              onClick={handleAnalyze}
              disabled={analyzing || !canAnalyze}
              className="rounded-lg bg-linear-to-r from-indigo-500 to-fuchsia-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {analyzing ? "Analyzing…" : "Analyze job"}
            </button>
          </div>
        </section>

        <section className="mt-8">
          <h2 className="text-lg font-semibold text-white">Saved analyses</h2>

          {loading ? (
            <p className="mt-4 animate-pulse text-sm text-slate-400">Loading analyses…</p>
          ) : jobs.length === 0 ? (
            <p className="mt-4 rounded-2xl border border-dashed border-white/10 bg-white/[0.02] px-6 py-10 text-center text-sm text-slate-400">
              No analyses yet. Paste a job description above to create one.
            </p>
          ) : (
            <ul className="mt-4 space-y-3">
              {jobs.map((job) => (
                <li key={job.id}>
                  <Link
                    to={`/jobs/${job.id}`}
                    className="flex items-center justify-between gap-4 rounded-xl border border-white/10 bg-white/[0.03] px-5 py-4 transition hover:border-indigo-400/40 hover:bg-white/[0.05]"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-white">{job.job_title}</p>
                      <p className="text-xs text-slate-500">{formatDate(job.created_at)}</p>
                    </div>
                    <span className="shrink-0 rounded-full border border-indigo-400/20 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-200">
                      {engineLabel(job.analysis_engine)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
      <Footer />
    </div>
  );
}
