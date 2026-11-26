import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import {
  createMatch,
  getApiErrorMessage,
  listJobs,
  listResumes,
  type JobSummary,
  type ResumeSummary,
} from "../lib/api";
import { parsePositiveId } from "../lib/validation";

export default function MatchSetupPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [resumes, setResumes] = useState<ResumeSummary[]>([]);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const initialJobId = searchParams.get("jobId");
  const [resumeId, setResumeId] = useState("");
  const [jobId, setJobId] = useState(
    parsePositiveId(initialJobId) !== null ? (initialJobId ?? "") : "",
  );
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([listResumes(), listJobs()])
      .then(([resumeData, jobData]) => {
        if (!active) return;
        setResumes(resumeData);
        setJobs(jobData);
        if (!resumeId && resumeData.length > 0) setResumeId(String(resumeData[0].id));
        if (!jobId && jobData.length > 0) setJobId(String(jobData[0].id));
        setLoading(false);
      })
      .catch((err) => {
        if (active) {
          setError(getApiErrorMessage(err));
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const numericResumeId = parsePositiveId(resumeId);
    const numericJobId = parsePositiveId(jobId);
    if (numericResumeId === null || numericJobId === null) {
      setError("Choose a valid resume and job description first.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const analysis = await createMatch(numericResumeId, numericJobId);
      navigate(`/analysis/${analysis.id}`);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  const ready = resumes.length > 0 && jobs.length > 0;

  return (
    <div className="min-h-screen bg-slate-950 font-sans text-slate-100">
      <Navbar />
      <main className="mx-auto max-w-3xl px-6 py-12">
        <h1 className="text-3xl font-bold tracking-tight text-white">Match my resume</h1>
        <p className="mt-2 text-slate-400">
          Choose a resume and a job description. The score is calculated by our
          deterministic backend rules — the AI never generates it.
        </p>

        <section className="mt-8 rounded-2xl border border-white/10 bg-white/[0.03] p-6">
          {loading ? (
            <p className="animate-pulse text-sm text-slate-400">Loading your data…</p>
          ) : !ready ? (
            <div className="space-y-3 text-sm text-slate-300">
              <p>You need both an uploaded resume and an analyzed job description.</p>
              <div className="flex flex-wrap gap-3">
                {resumes.length === 0 && (
                  <a href="/resumes" className="text-indigo-300 hover:text-indigo-200">
                    Upload a resume →
                  </a>
                )}
                {jobs.length === 0 && (
                  <a href="/jobs" className="text-indigo-300 hover:text-indigo-200">
                    Analyze a job →
                  </a>
                )}
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <p className="rounded-lg border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
                  {error}
                </p>
              )}

              <div>
                <label htmlFor="resume" className="mb-1 block text-sm font-medium text-slate-300">
                  Resume
                </label>
                <select
                  id="resume"
                  value={resumeId}
                  onChange={(event) => setResumeId(event.target.value)}
                  className="w-full rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2 text-sm text-white outline-none focus:border-indigo-400"
                >
                  {resumes.map((resume) => (
                    <option key={resume.id} value={resume.id}>
                      {resume.name ?? resume.original_filename} · {resume.original_filename}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="job" className="mb-1 block text-sm font-medium text-slate-300">
                  Job description
                </label>
                <select
                  id="job"
                  value={jobId}
                  onChange={(event) => setJobId(event.target.value)}
                  className="w-full rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2 text-sm text-white outline-none focus:border-indigo-400"
                >
                  {jobs.map((job) => (
                    <option key={job.id} value={job.id}>
                      {job.job_title}
                    </option>
                  ))}
                </select>
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="rounded-lg bg-linear-to-r from-indigo-500 to-fuchsia-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting ? "Calculating…" : "Calculate match"}
              </button>
            </form>
          )}
        </section>
      </main>
      <Footer />
    </div>
  );
}
