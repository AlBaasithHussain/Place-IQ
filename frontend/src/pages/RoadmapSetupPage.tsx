import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import {
  generateRoadmap,
  getApiErrorMessage,
  listAnalyses,
  listRoadmaps,
  type AnalysisSummary,
  type RoadmapSummary,
} from "../lib/api";
import { formatDate } from "../lib/format";
import { parsePositiveId } from "../lib/validation";

export default function RoadmapSetupPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [analyses, setAnalyses] = useState<AnalysisSummary[]>([]);
  const [roadmaps, setRoadmaps] = useState<RoadmapSummary[]>([]);
  const initialAnalysisId = searchParams.get("analysisId");
  const [analysisId, setAnalysisId] = useState(
    parsePositiveId(initialAnalysisId) !== null ? (initialAnalysisId ?? "") : "",
  );
  const [durationDays, setDurationDays] = useState<7 | 14>(7);
  const [hoursPerDay, setHoursPerDay] = useState("1");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([listAnalyses(), listRoadmaps()])
      .then(([analysisData, roadmapData]) => {
        if (!active) return;
        setAnalyses(analysisData);
        setRoadmaps(roadmapData);
        if (!analysisId && analysisData.length > 0) {
          setAnalysisId(String(analysisData[0].id));
        }
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
    const hours = Number(hoursPerDay);
    const numericAnalysisId = parsePositiveId(analysisId);
    if (numericAnalysisId === null || !Number.isFinite(hours) || hours < 0.25 || hours > 8) {
      setError("Choose a valid analysis and enter 0.25–8 study hours per day.");
      return;
    }
    setGenerating(true);
    setError(null);
    try {
      const roadmap = await generateRoadmap({
        analysis_id: numericAnalysisId,
        duration_days: durationDays,
        hours_per_day: hours,
      });
      navigate(`/roadmaps/${roadmap.id}`);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 font-sans text-slate-100">
      <Navbar />
      <main className="mx-auto max-w-5xl px-6 py-12">
        <h1 className="text-3xl font-bold tracking-tight text-white">Learning roadmap</h1>
        <p className="mt-2 text-slate-400">
          Turn your skill gaps into a daily plan. AI recommends the topics and
          practice; the backend validates and stores every day.
        </p>

        <section className="mt-8 rounded-2xl border border-white/10 bg-white/[0.03] p-6">
          {loading ? (
            <p className="animate-pulse text-sm text-slate-400">Loading your matches…</p>
          ) : analyses.length === 0 ? (
            <div className="space-y-3 text-sm text-slate-300">
              <p>You need a saved resume↔job match before generating a roadmap.</p>
              <Link
                to="/analysis/new"
                className="inline-block text-indigo-300 transition hover:text-indigo-200"
              >
                Create a match →
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6">
              {error && (
                <p className="rounded-lg border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
                  {error}
                </p>
              )}

              <div>
                <label htmlFor="analysis" className="mb-1 block text-sm font-medium text-slate-300">
                  Match to build on
                </label>
                <select
                  id="analysis"
                  value={analysisId}
                  onChange={(event) => setAnalysisId(event.target.value)}
                  className="w-full rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2 text-sm text-white outline-none focus:border-indigo-400"
                >
                  {analyses.map((analysis) => (
                    <option key={analysis.id} value={analysis.id}>
                      Match #{analysis.id} · resume #{analysis.resume_id} · job #
                      {analysis.job_id} · {analysis.score}/100
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <span className="mb-2 block text-sm font-medium text-slate-300">Duration</span>
                <div className="flex gap-3">
                  {([7, 14] as const).map((days) => (
                    <button
                      key={days}
                      type="button"
                      onClick={() => setDurationDays(days)}
                      className={`rounded-lg border px-4 py-2 text-sm font-semibold transition ${
                        durationDays === days
                          ? "border-indigo-400/40 bg-indigo-500/15 text-indigo-100"
                          : "border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
                      }`}
                    >
                      {days} days
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label htmlFor="hours" className="mb-1 block text-sm font-medium text-slate-300">
                  Study time per day (hours)
                </label>
                <input
                  id="hours"
                  type="number"
                  min="0.25"
                  max="8"
                  step="0.25"
                  value={hoursPerDay}
                  onChange={(event) => setHoursPerDay(event.target.value)}
                  className="w-40 rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2 text-sm text-white outline-none focus:border-indigo-400"
                />
                <p className="mt-1 text-xs text-slate-500">
                  Each day&apos;s tasks are sized to fit this budget.
                </p>
              </div>

              <button
                type="submit"
                disabled={generating}
                className="rounded-lg bg-linear-to-r from-indigo-500 to-fuchsia-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {generating ? "Building roadmap…" : "Generate roadmap"}
              </button>
            </form>
          )}
        </section>

        <section className="mt-10">
          <h2 className="text-lg font-semibold text-white">Saved roadmaps</h2>
          {roadmaps.length === 0 ? (
            <p className="mt-4 rounded-2xl border border-dashed border-white/10 bg-white/[0.02] px-6 py-10 text-center text-sm text-slate-400">
              No roadmaps yet. Generate one above.
            </p>
          ) : (
            <ul className="mt-4 space-y-3">
              {roadmaps.map((roadmap) => (
                <li key={roadmap.id}>
                  <Link
                    to={`/roadmaps/${roadmap.id}`}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.03] px-5 py-4 transition hover:border-indigo-400/40 hover:bg-white/[0.05]"
                  >
                    <div>
                      <p className="font-semibold text-white">{roadmap.job_title}</p>
                      <p className="text-xs text-slate-500">
                        {roadmap.duration_days} days · {roadmap.match_score}/100 ·{" "}
                        {formatDate(roadmap.created_at)}
                      </p>
                    </div>
                    <span className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-200">
                      {roadmap.progress_percentage}% complete
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
