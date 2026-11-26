import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import {
  getApiErrorMessage,
  getInterviewResults,
  type AnswerEvaluation,
  type EvaluationResult,
  type QuestionCategory,
} from "../lib/api";
import { formatDate } from "../lib/format";

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

function scoreColor(score: number): string {
  if (score >= 75) return "text-emerald-300";
  if (score >= 50) return "text-amber-300";
  return "text-rose-300";
}

function barColor(score: number): string {
  if (score >= 75) return "bg-emerald-400";
  if (score >= 50) return "bg-amber-400";
  return "bg-rose-400";
}

function FeedbackList({ title, items, tone }: { title: string; items: string[]; tone: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
      <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
      <ul className="mt-3 space-y-2">
        {items.map((item, index) => (
          <li key={`${item}-${index}`} className={`flex gap-2 text-sm ${tone}`}>
            <span aria-hidden="true">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function CriterionBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <span className="font-medium text-slate-300">{label}</span>
        <span className="text-slate-400">{value}/100</span>
      </div>
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-white/5">
        <div className={`h-full rounded-full ${barColor(value)}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function AnswerCard({ answer }: { answer: AnswerEvaluation }) {
  return (
    <article className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-indigo-300">
              Question {answer.position} · {answer.score}/100
            </span>
            <span
              className={`rounded-full border px-2 py-0.5 text-xs font-medium ${CATEGORY_STYLE[answer.category]}`}
            >
              {CATEGORY_LABEL[answer.category]}
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-xs text-slate-300">
              Focus: {answer.focus_skill}
            </span>
          </div>
          <h2 className="mt-3 text-lg font-semibold leading-snug text-white">{answer.question}</h2>
        </div>
        <span className={`text-3xl font-extrabold ${scoreColor(answer.score)}`}>
          {answer.score}
        </span>
      </div>

      <div className="mt-5 grid gap-5 md:grid-cols-2">
        <CriterionBar label="Technical accuracy" value={answer.technical_accuracy} />
        <CriterionBar label="Relevance" value={answer.relevance} />
        <CriterionBar label="Completeness" value={answer.completeness} />
        <CriterionBar label="Clarity" value={answer.clarity} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <FeedbackList title="Strengths" items={answer.strengths} tone="text-emerald-200" />
        <FeedbackList title="Weaknesses" items={answer.weaknesses} tone="text-rose-200" />
      </div>

      <div className="mt-4 rounded-xl border border-amber-400/20 bg-amber-500/[0.05] p-4">
        <h3 className="text-sm font-semibold text-amber-200">Suggested improvement</h3>
        <p className="mt-2 text-sm leading-relaxed text-slate-300">
          {answer.suggested_improvement}
        </p>
      </div>

      <div className="mt-4 rounded-xl border border-indigo-400/20 bg-indigo-500/[0.05] p-4">
        <h3 className="text-sm font-semibold text-indigo-200">Model answer</h3>
        <p className="mt-2 text-sm leading-relaxed text-slate-300">{answer.model_answer}</p>
      </div>

      <div className="mt-4 rounded-xl border border-white/10 bg-slate-950/40 p-4">
        <h3 className="text-sm font-semibold text-slate-300">Your answer</h3>
        <p className="mt-2 text-sm leading-relaxed text-slate-400">{answer.answer}</p>
      </div>
    </article>
  );
}

export default function InterviewResultsPage() {
  const { id } = useParams<{ id: string }>();

  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [loading, setLoading] = useState(true);
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
    getInterviewResults(numericId)
      .then((data) => {
        if (active) setResult(data);
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
          to={`/interviews/${id}`}
          className="text-sm font-medium text-indigo-300 transition hover:text-indigo-200"
        >
          ← Back to interview
        </Link>

        {loading ? (
          <p className="mt-6 animate-pulse text-sm text-slate-400">Loading evaluation…</p>
        ) : error || !result ? (
          <p className="mt-6 rounded-lg border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error ?? "No evaluation found."}
          </p>
        ) : (
          <>
            <header className="mt-4 flex flex-wrap items-end justify-between gap-4">
              <div>
                <h1 className="text-3xl font-bold tracking-tight text-white">Interview evaluation</h1>
                <p className="mt-1 text-slate-400">
                  {result.job_title} · {result.evaluated_answer_count} answers ·{" "}
                  {formatDate(result.created_at)}
                </p>
              </div>
              <span className="rounded-full border border-indigo-400/20 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-200">
                {result.generation_engine === "llm" ? "AI evaluation" : "Local evaluation"}
              </span>
            </header>

            <section className="mt-6 grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 md:col-span-1">
                <p className="text-sm font-semibold uppercase tracking-wide text-slate-400">
                  Overall score
                </p>
                <p className={`mt-3 text-6xl font-extrabold tracking-tight ${scoreColor(result.overall_score)}`}>
                  {result.overall_score}
                  <span className="ml-1 text-2xl text-slate-500">/ 100</span>
                </p>
                <div className="mt-4 h-3 w-full overflow-hidden rounded-full bg-white/5">
                  <div
                    className={`h-full rounded-full ${barColor(result.overall_score)}`}
                    style={{ width: `${result.overall_score}%` }}
                  />
                </div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 md:col-span-2">
                <h2 className="text-lg font-semibold text-white">Summary</h2>
                <p className="mt-2 text-sm leading-relaxed text-slate-300">
                  {result.overall_summary}
                </p>
                <p className="mt-4 text-xs text-slate-500">
                  Evaluates written answer content on technical accuracy, relevance,
                  completeness and clarity only. It does not measure emotions or personality.
                </p>
              </div>
            </section>

            <section className="mt-6 grid gap-4 lg:grid-cols-3">
              <FeedbackList title="Strengths" items={result.overall_strengths} tone="text-emerald-200" />
              <FeedbackList title="Weaknesses" items={result.overall_weaknesses} tone="text-rose-200" />
              <FeedbackList
                title="Suggested improvement"
                items={result.suggested_improvements}
                tone="text-amber-200"
              />
            </section>

            <section className="mt-10 space-y-4">
              {result.answer_evaluations.map((answer) => (
                <AnswerCard key={answer.id} answer={answer} />
              ))}
            </section>
          </>
        )}
      </main>
      <Footer />
    </div>
  );
}
