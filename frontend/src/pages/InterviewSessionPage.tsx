import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import axios from "axios";

import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import {
  answerInterviewQuestion,
  evaluateInterview,
  getApiErrorMessage,
  getInterview,
  getInterviewResults,
  type EvaluationResult,
  type InterviewDetail,
  type QuestionCategory,
} from "../lib/api";
import { formatDate } from "../lib/format";

const MAX_ANSWER_LENGTH = 10000;

const CATEGORY_LABEL: Record<QuestionCategory, string> = {
  technical: "Technical",
  hr: "HR",
  behavioral: "Behavioral",
  project_based: "Project-based",
  problem_solving: "Problem-solving",
};

const CATEGORY_STYLE: Record<QuestionCategory, string> = {
  technical: "border-indigo-400/30 bg-indigo-500/10 text-indigo-200",
  hr: "border-fuchsia-400/30 bg-fuchsia-500/10 text-fuchsia-200",
  behavioral: "border-amber-400/30 bg-amber-500/10 text-amber-200",
  project_based: "border-emerald-400/30 bg-emerald-500/10 text-emerald-200",
  problem_solving: "border-sky-400/30 bg-sky-500/10 text-sky-200",
};

export default function InterviewSessionPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [interview, setInterview] = useState<InterviewDetail | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationResult | null>(null);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const numericId = Number(id);
    if (!Number.isInteger(numericId) || numericId <= 0) {
      setError("Invalid interview id.");
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    Promise.all([
      getInterview(numericId),
      getInterviewResults(numericId).catch((err) => {
        if (axios.isAxiosError(err) && err.response?.status === 404) return null;
        throw err;
      }),
    ])
      .then(([data, evaluationData]) => {
        if (active) {
          setInterview(data);
          setEvaluation(evaluationData);
        }
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

  const current = interview?.questions.find(
    (item) => item.position === interview.current_question_number,
  );
  const currentQuestionId = current?.id;

  useEffect(() => {
    setAnswer("");
  }, [currentQuestionId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!interview || !current) return;
    if (answer.trim().length === 0) {
      setError("Write an answer before submitting.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const updated = await answerInterviewQuestion(
        interview.id,
        current.id,
        answer.trim(),
      );
      setInterview(updated);
      setAnswer("");
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleEvaluate() {
    if (!interview) return;
    setEvaluating(true);
    setError(null);
    try {
      const result = await evaluateInterview(interview.id);
      setEvaluation(result);
      navigate(`/interviews/${interview.id}/results`);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setEvaluating(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 font-sans text-slate-100">
      <Navbar />
      <main className="mx-auto max-w-5xl px-6 py-12">
        <Link
          to="/interviews/start"
          className="text-sm font-medium text-indigo-300 transition hover:text-indigo-200"
        >
          ← Mock interviews
        </Link>

        {loading ? (
          <p className="mt-6 animate-pulse text-sm text-slate-400">Loading interview…</p>
        ) : error && !interview ? (
          <p className="mt-6 rounded-lg border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </p>
        ) : interview ? (
          <>
            <header className="mt-4 flex flex-wrap items-end justify-between gap-4">
              <div>
                <h1 className="text-3xl font-bold tracking-tight text-white">
                  {interview.job_title}
                </h1>
                <p className="mt-1 text-slate-400">
                  {interview.question_count} questions · {formatDate(interview.created_at)} ·{" "}
                  {interview.generation_engine === "llm" ? "AI-generated" : "offline-generated"}
                </p>
              </div>
              <span className="rounded-full border border-indigo-400/30 bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-200">
                {interview.status === "completed" ? "Completed" : "In progress"}
              </span>
            </header>

            <section className="mt-6 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
                <span className="font-medium text-slate-200">
                  {interview.answered_count} of {interview.question_count} answered
                </span>
                <span className="text-slate-400">{interview.progress_percentage}%</span>
              </div>
              <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-white/5">
                <div
                  className="h-full rounded-full bg-linear-to-r from-indigo-400 to-fuchsia-400"
                  style={{ width: `${interview.progress_percentage}%` }}
                />
              </div>
            </section>

            {error && (
              <p className="mt-4 rounded-lg border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                {error}
              </p>
            )}

            {interview.is_complete ? (
              <section className="mt-8 rounded-2xl border border-emerald-400/20 bg-emerald-500/[0.04] p-6">
                <h2 className="text-xl font-semibold text-white">Interview complete</h2>
                <p className="mt-1 text-sm text-slate-400">
                  You answered all {interview.question_count} questions. Review your responses below.
                </p>
                {interview.completed_at && (
                  <p className="mt-1 text-xs text-slate-500">
                    Finished {formatDate(interview.completed_at)}
                  </p>
                )}
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  {interview.has_evaluation || evaluation ? (
                    <Link
                      to={`/interviews/${interview.id}/results`}
                      className="rounded-lg border border-emerald-400/30 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-200 transition hover:bg-emerald-500/20"
                    >
                      View evaluation →
                    </Link>
                  ) : (
                    <button
                      onClick={handleEvaluate}
                      disabled={evaluating}
                      className="rounded-lg bg-linear-to-r from-indigo-500 to-fuchsia-500 px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {evaluating ? "Evaluating answers…" : "Evaluate answers"}
                    </button>
                  )}
                  <span className="text-xs text-slate-500">
                    Content-based feedback only; no emotion or personality scoring.
                  </span>
                </div>
              </section>
            ) : current ? (
              <section className="mt-8 rounded-2xl border border-indigo-400/20 bg-indigo-500/[0.04] p-6">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-slate-300">
                    Question {current.position} / {interview.question_count}
                  </span>
                  <span
                    className={`rounded-full border px-3 py-1 text-xs font-medium ${CATEGORY_STYLE[current.category]}`}
                  >
                    {CATEGORY_LABEL[current.category]}
                  </span>
                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-slate-300">
                    Focus: {current.focus_skill}
                  </span>
                </div>
                <h2 className="mt-4 text-xl font-semibold leading-snug text-white">
                  {current.question}
                </h2>

                <form onSubmit={handleSubmit} className="mt-5">
                  <label
                    htmlFor="interview-answer"
                    className="mb-2 block text-sm font-medium text-slate-300"
                  >
                    Your answer
                  </label>
                  <textarea
                    id="interview-answer"
                    value={answer}
                    onChange={(event) => setAnswer(event.target.value)}
                    rows={8}
                    maxLength={MAX_ANSWER_LENGTH}
                    placeholder="Structure your answer: context, action, result…"
                    className="w-full rounded-lg border border-white/10 bg-slate-900/60 px-4 py-3 text-sm leading-relaxed text-white outline-none placeholder:text-slate-600 focus:border-indigo-400"
                  />
                  <p className="mt-2 text-right text-xs text-slate-500">
                    {answer.length}/{MAX_ANSWER_LENGTH} characters
                  </p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <button
                      type="submit"
                      disabled={submitting}
                      className="rounded-lg bg-linear-to-r from-indigo-500 to-fuchsia-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {submitting
                        ? "Saving…"
                        : current.position === interview.question_count
                          ? "Finish interview"
                          : "Submit answer & next"}
                    </button>
                  </div>
                </form>
              </section>
            ) : null}

            <section className="mt-10">
              <h2 className="text-lg font-semibold text-white">Question review</h2>
              <ol className="mt-4 space-y-3">
                {interview.questions.map((question) => (
                  <li
                    key={question.id}
                    className="rounded-xl border border-white/10 bg-white/[0.03] p-5"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-slate-200">
                        {question.position}. {question.question}
                      </p>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-xs font-medium ${CATEGORY_STYLE[question.category]}`}
                      >
                        {CATEGORY_LABEL[question.category]}
                      </span>
                    </div>
                    <p className="mt-2 text-sm leading-relaxed text-slate-400">
                      {question.answer ?? "Not answered yet."}
                    </p>
                  </li>
                ))}
              </ol>
            </section>
          </>
        ) : null}
      </main>
      <Footer />
    </div>
  );
}
