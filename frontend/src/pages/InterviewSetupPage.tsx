import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import {
  getApiErrorMessage,
  listInterviews,
  listJobs,
  listResumes,
  startInterview,
  type InterviewSummary,
  type JobSummary,
  type ResumeSummary,
} from "../lib/api";
import { formatDate } from "../lib/format";
import { parsePositiveId } from "../lib/validation";

export default function InterviewSetupPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [resumes, setResumes] = useState<ResumeSummary[]>([]);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [interviews, setInterviews] = useState<InterviewSummary[]>([]);
  const initialResumeId = searchParams.get("resumeId");
  const initialJobId = searchParams.get("jobId");
  const [resumeId, setResumeId] = useState(
    parsePositiveId(initialResumeId) !== null ? (initialResumeId ?? "") : "",
  );
  const [jobId, setJobId] = useState(
    parsePositiveId(initialJobId) !== null ? (initialJobId ?? "") : "",
  );
  const [questionCount, setQuestionCount] = useState("5");
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([listResumes(), listJobs(), listInterviews()])
      .then(([resumeData, jobData, interviewData]) => {
        if (!active) return;
        setResumes(resumeData);
        setJobs(jobData);
        setInterviews(interviewData);
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
    const count = Number(questionCount);
    const numericResumeId = parsePositiveId(resumeId);
    const numericJobId = parsePositiveId(jobId);
    if (
      numericResumeId === null ||
      numericJobId === null ||
      !Number.isInteger(count) ||
      count < 5 ||
      count > 10
    ) {
      setError("Choose a valid resume, job and 5–10 questions.");
      return;
    }
    setStarting(true);
    setError(null);
    try {
      const interview = await startInterview({
        resume_id: numericResumeId,
        job_id: numericJobId,
        question_count: count,
      });
      navigate(`/interviews/${interview.id}`);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setStarting(false);
    }
  }

  const ready = resumes.length > 0 && jobs.length > 0;

  return (
    <div className="min-h-screen bg-slate-950 font-sans text-slate-100">
      <Navbar />
      <main className="mx-auto max-w-5xl px-6 py-12">
        <h1 className="text-3xl font-bold tracking-tight text-white">Mock interview</h1>
        <p className="mt-2 text-slate-400">
          AI builds a tailored question set from your resume, the job description,
          your projects and your skill gaps. Answer with text for now — voice is
          not implemented yet.
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
            <form onSubmit={handleSubmit} className="grid gap-5 md:grid-cols-3">
              {error && (
                <p className="md:col-span-3 rounded-lg border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
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
                      {resume.name ?? resume.original_filename}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="job" className="mb-1 block text-sm font-medium text-slate-300">
                  Target job
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

              <div>
                <label htmlFor="count" className="mb-1 block text-sm font-medium text-slate-300">
                  Questions (5–10)
                </label>
                <input
                  id="count"
                  type="number"
                  min="5"
                  max="10"
                  value={questionCount}
                  onChange={(event) => setQuestionCount(event.target.value)}
                  className="w-full rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2 text-sm text-white outline-none focus:border-indigo-400"
                />
              </div>

              <div className="md:col-span-3">
                <button
                  type="submit"
                  disabled={starting}
                  className="rounded-lg bg-linear-to-r from-indigo-500 to-fuchsia-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {starting ? "Generating questions…" : "Start interview"}
                </button>
              </div>
            </form>
          )}
        </section>

        <section className="mt-10">
          <h2 className="text-lg font-semibold text-white">Past sessions</h2>
          {interviews.length === 0 ? (
            <p className="mt-4 rounded-2xl border border-dashed border-white/10 bg-white/[0.02] px-6 py-10 text-center text-sm text-slate-400">
              No interviews yet. Start one above.
            </p>
          ) : (
            <ul className="mt-4 space-y-3">
              {interviews.map((interview) => (
                <li
                  key={interview.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.03] px-5 py-4"
                >
                  <Link
                    to={`/interviews/${interview.id}`}
                    className="flex flex-1 flex-wrap items-center justify-between gap-3"
                  >
                    <div>
                      <p className="font-semibold text-white">{interview.job_title}</p>
                      <p className="text-xs text-slate-500">
                        {interview.question_count} questions · {formatDate(interview.created_at)}
                      </p>
                    </div>
                    <span className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-200">
                      {interview.progress_percentage}% answered
                    </span>
                  </Link>
                  {interview.has_evaluation && (
                    <Link
                      to={`/interviews/${interview.id}/results`}
                      className="text-sm font-medium text-indigo-300 hover:text-indigo-200"
                    >
                      View results →
                    </Link>
                  )}
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
