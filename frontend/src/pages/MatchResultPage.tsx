import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import {
  getAnalysis,
  getApiErrorMessage,
  type BreakdownPart,
  type MatchDetail,
  type SkillStatus,
} from "../lib/api";
import { formatDate } from "../lib/format";

const STATUS_LABEL: Record<SkillStatus, string> = {
  match: "MATCH",
  partial: "PARTIAL",
  missing: "MISSING",
};

const STATUS_STYLE: Record<SkillStatus, string> = {
  match: "border-emerald-400/30 bg-emerald-500/10 text-emerald-200",
  partial: "border-amber-400/30 bg-amber-500/10 text-amber-200",
  missing: "border-rose-400/30 bg-rose-500/10 text-rose-200",
};

const TYPE_LABEL: Record<string, string> = {
  required: "Required",
  preferred: "Preferred",
  soft: "Soft skill",
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

function ChipList({ items, tone }: { items: string[]; tone: "match" | "partial" | "missing" | "bonus" }) {
  const tones = {
    match: "border-emerald-400/30 bg-emerald-500/10 text-emerald-200",
    partial: "border-amber-400/30 bg-amber-500/10 text-amber-200",
    missing: "border-rose-400/30 bg-rose-500/10 text-rose-200",
    bonus: "border-indigo-400/30 bg-indigo-500/10 text-indigo-200",
  };
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">None</p>;
  }
  return (
    <ul className="flex flex-wrap gap-2">
      {items.map((item, index) => (
        <li
          key={`${item}-${index}`}
          className={`rounded-full border px-3 py-1 text-xs font-medium ${tones[tone]}`}
        >
          {item}
        </li>
      ))}
    </ul>
  );
}

function ProgressRow({ label, part }: { label: string; part: BreakdownPart }) {
  const percent = Math.round(part.credit * 100);
  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
        <span className="font-medium text-slate-200">{label}</span>
        <span className="text-slate-400">
          {part.points} / {Math.round(part.weight * 100)} pts · {percent}%
        </span>
      </div>
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-white/5">
        <div
          className={`h-full rounded-full ${barColor(percent)}`}
          style={{ width: `${percent}%` }}
        />
      </div>
      <p className="mt-1 text-xs text-slate-500">
        Weight {Math.round(part.weight * 100)}% · credit {part.credit.toFixed(2)}
        {Object.keys(part.details).length > 0 ? ` · ${JSON.stringify(part.details)}` : ""}
      </p>
    </div>
  );
}

export default function MatchResultPage() {
  const { id } = useParams<{ id: string }>();

  const [analysis, setAnalysis] = useState<MatchDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const numericId = Number(id);
    if (!Number.isInteger(numericId) || numericId <= 0) {
      setError("Invalid analysis id.");
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    getAnalysis(numericId)
      .then((data) => {
        if (active) setAnalysis(data);
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
          to="/analysis/new"
          className="text-sm font-medium text-indigo-300 transition hover:text-indigo-200"
        >
          ← New match
        </Link>

        {loading ? (
          <p className="mt-6 animate-pulse text-sm text-slate-400">Loading result…</p>
        ) : error ? (
          <p className="mt-6 rounded-lg border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </p>
        ) : analysis ? (
          <>
            <header className="mt-4 flex flex-wrap items-end justify-between gap-4">
              <div>
                <h1 className="text-3xl font-bold tracking-tight text-white">Match result</h1>
                <p className="mt-1 text-slate-400">
                  Resume #{analysis.resume_id} vs job #{analysis.job_id} ·{" "}
                  {formatDate(analysis.created_at)}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-4">
                <Link
                  to={`/jobs/${analysis.job_id}`}
                  className="text-sm font-medium text-indigo-300 hover:text-indigo-200"
                >
                  View job description →
                </Link>
                <Link
                  to={`/interviews/start?resumeId=${analysis.resume_id}&jobId=${analysis.job_id}`}
                  className="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:bg-white/10"
                >
                  Start mock interview →
                </Link>
                <Link
                  to={`/roadmaps/new?analysisId=${analysis.id}`}
                  className="rounded-lg bg-linear-to-r from-indigo-500 to-fuchsia-500 px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
                >
                  Generate roadmap →
                </Link>
              </div>
            </header>

            <section className="mt-8 grid gap-6 lg:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 lg:col-span-1">
                <p className="text-sm font-semibold uppercase tracking-wide text-slate-400">
                  Job match score
                </p>
                <p className={`mt-3 text-6xl font-extrabold tracking-tight ${scoreColor(analysis.score)}`}>
                  {analysis.score}
                  <span className="ml-1 text-2xl text-slate-500">/ 100</span>
                </p>
                <div className="mt-4 h-3 w-full overflow-hidden rounded-full bg-white/5">
                  <div
                    className={`h-full rounded-full ${barColor(analysis.score)}`}
                    style={{ width: `${analysis.score}%` }}
                  />
                </div>
                <p className="mt-3 text-xs text-slate-500">
                  Calculated by backend rules. The AI never generates this number.
                </p>
              </div>

              <div className="space-y-5 rounded-2xl border border-white/10 bg-white/[0.03] p-6 lg:col-span-2">
                <ProgressRow label="Required skills" part={analysis.breakdown.required_skills} />
                <ProgressRow label="Preferred skills" part={analysis.breakdown.preferred_skills} />
                <ProgressRow
                  label="Projects & experience"
                  part={analysis.breakdown.projects_experience}
                />
                <ProgressRow label="Soft skills" part={analysis.breakdown.soft_skills} />
              </div>
            </section>

            <section className="mt-8 grid gap-6 lg:grid-cols-2">
              <div className="rounded-2xl border border-emerald-400/20 bg-emerald-500/[0.04] p-6">
                <h2 className="text-lg font-semibold text-white">Matching skills</h2>
                <p className="mt-1 text-sm text-slate-400">Direct matches worth full credit.</p>
                <div className="mt-4">
                  <ChipList items={analysis.matching_skills} tone="match" />
                </div>
              </div>
              <div className="rounded-2xl border border-rose-400/20 bg-rose-500/[0.04] p-6">
                <h2 className="text-lg font-semibold text-white">Missing skills</h2>
                <p className="mt-1 text-sm text-slate-400">Not present and not closely related.</p>
                <div className="mt-4">
                  <ChipList items={analysis.missing_skills} tone="missing" />
                </div>
              </div>
              <div className="rounded-2xl border border-amber-400/20 bg-amber-500/[0.04] p-6">
                <h2 className="text-lg font-semibold text-white">Partial skills</h2>
                <p className="mt-1 text-sm text-slate-400">A curated close relative was found.</p>
                <div className="mt-4">
                  <ChipList items={analysis.partial_skills} tone="partial" />
                </div>
              </div>
              <div className="rounded-2xl border border-indigo-400/20 bg-indigo-500/[0.04] p-6">
                <h2 className="text-lg font-semibold text-white">Bonus skills</h2>
                <p className="mt-1 text-sm text-slate-400">Nice-to-haves you already bring.</p>
                <div className="mt-4">
                  <ChipList items={analysis.bonus_skills} tone="bonus" />
                </div>
              </div>
            </section>

            <section className="mt-8 rounded-2xl border border-white/10 bg-white/[0.03] p-6">
              <h2 className="text-lg font-semibold text-white">Skill comparison</h2>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-white/10 text-xs uppercase tracking-wide text-slate-400">
                      <th className="py-2 pr-4">Skill</th>
                      <th className="py-2 pr-4">Requirement</th>
                      <th className="py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analysis.comparisons.map((comparison, index) => (
                      <tr
                        key={`${comparison.skill}-${comparison.requirement_type}-${index}`}
                        className="border-b border-white/5 last:border-0"
                      >
                        <td className="py-2 pr-4 text-slate-200">{comparison.skill}</td>
                        <td className="py-2 pr-4 text-slate-400">
                          {TYPE_LABEL[comparison.requirement_type] ?? comparison.requirement_type}
                        </td>
                        <td className="py-2">
                          <span
                            className={`inline-block rounded-full border px-2 py-0.5 text-xs font-semibold ${STATUS_STYLE[comparison.status]}`}
                          >
                            {STATUS_LABEL[comparison.status]}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="mt-6 rounded-2xl border border-white/10 bg-white/[0.03] p-6">
              <h2 className="text-lg font-semibold text-white">How the score is calculated</h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-300">
                {analysis.explanation}
              </p>
            </section>
          </>
        ) : null}
      </main>
      <Footer />
    </div>
  );
}
