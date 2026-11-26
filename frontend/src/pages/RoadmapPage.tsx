import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import {
  getApiErrorMessage,
  getRoadmap,
  updateRoadmapTask,
  type PriorityLevel,
  type RoadmapDetail,
  type RoadmapTask,
} from "../lib/api";
import { formatDate } from "../lib/format";

const PRIORITY_STYLE: Record<PriorityLevel, string> = {
  high: "border-rose-400/30 bg-rose-500/10 text-rose-200",
  medium: "border-amber-400/30 bg-amber-500/10 text-amber-200",
  low: "border-slate-400/30 bg-slate-500/10 text-slate-300",
};

const PRIORITY_LABEL: Record<PriorityLevel, string> = {
  high: "High priority",
  medium: "Medium priority",
  low: "Low priority",
};

function formatMinutes(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest === 0 ? `${hours} h` : `${hours} h ${rest} min`;
}

function TaskCard({
  task,
  roadmapId,
  updating,
  onToggle,
}: {
  task: RoadmapTask;
  roadmapId: number;
  updating: boolean;
  onToggle: (task: RoadmapTask) => void;
}) {
  return (
    <article
      className={`rounded-2xl border p-5 transition ${
        task.completed
          ? "border-emerald-400/20 bg-emerald-500/[0.05]"
          : "border-white/10 bg-white/[0.03]"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            checked={task.completed}
            disabled={updating}
            onChange={() => onToggle(task)}
            aria-label={`Mark day ${task.day} complete`}
            className="mt-1 h-5 w-5 shrink-0 cursor-pointer accent-indigo-400 disabled:cursor-wait"
          />
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-300">
              Day {task.day} · {formatMinutes(task.estimated_minutes)}
            </p>
            <h2
              className={`mt-1 text-lg font-semibold ${
                task.completed ? "text-slate-400 line-through" : "text-white"
              }`}
            >
              {task.title}
            </h2>
          </div>
        </div>
        <span
          className={`shrink-0 rounded-full border px-3 py-1 text-xs font-medium ${PRIORITY_STYLE[task.priority]}`}
        >
          {PRIORITY_LABEL[task.priority]}
        </span>
      </div>

      <div className="mt-5 grid gap-5 md:grid-cols-3">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Learn
          </h3>
          <ul className="mt-2 space-y-1">
            {task.learning_topics.map((topic, index) => (
              <li key={`${topic}-${index}`} className="text-sm text-slate-300">
                • {topic}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Practice
          </h3>
          <ul className="mt-2 space-y-1">
            {task.practice_tasks.map((practice, index) => (
              <li key={`${practice}-${index}`} className="text-sm text-slate-300">
                • {practice}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Mini project
          </h3>
          <p className="mt-2 text-sm text-slate-300">{task.mini_project}</p>
          <p className="mt-2 text-xs text-slate-500">Roadmap #{roadmapId}</p>
        </div>
      </div>
    </article>
  );
}

export default function RoadmapPage() {
  const { id } = useParams<{ id: string }>();

  const [roadmap, setRoadmap] = useState<RoadmapDetail | null>(null);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const numericId = Number(id);
    if (!Number.isInteger(numericId) || numericId <= 0) {
      setError("Invalid roadmap id.");
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    getRoadmap(numericId)
      .then((data) => {
        if (active) setRoadmap(data);
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

  async function handleToggle(task: RoadmapTask) {
    if (!roadmap || updatingId !== null) return;
    setUpdatingId(task.id);
    setError(null);
    try {
      const updated = await updateRoadmapTask(roadmap.id, task.id, !task.completed);
      setRoadmap(updated);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setUpdatingId(null);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 font-sans text-slate-100">
      <Navbar />
      <main className="mx-auto max-w-5xl px-6 py-12">
        <Link
          to="/roadmaps/new"
          className="text-sm font-medium text-indigo-300 transition hover:text-indigo-200"
        >
          ← New roadmap
        </Link>

        {loading ? (
          <p className="mt-6 animate-pulse text-sm text-slate-400">Loading roadmap…</p>
        ) : error ? (
          <p className="mt-6 rounded-lg border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </p>
        ) : roadmap ? (
          <>
            <header className="mt-4 flex flex-wrap items-end justify-between gap-4">
              <div>
                <h1 className="text-3xl font-bold tracking-tight text-white">
                  {roadmap.job_title}
                </h1>
                <p className="mt-1 text-slate-400">
                  {roadmap.duration_days}-day plan · match score {roadmap.match_score}/100 ·{" "}
                  {formatDate(roadmap.created_at)}
                </p>
              </div>
              <span className="rounded-full border border-indigo-400/20 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-200">
                {roadmap.generation_engine === "llm" ? "AI recommendations" : "Local recommendations"}
              </span>
            </header>

            <section className="mt-8 rounded-2xl border border-white/10 bg-white/[0.03] p-6">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wide text-slate-400">
                    Your progress
                  </p>
                  <p className="mt-2 text-5xl font-extrabold text-emerald-300">
                    {roadmap.progress_percentage}%
                  </p>
                  <p className="mt-1 text-sm text-slate-400">
                    {roadmap.completed_count} of {roadmap.tasks.length} days complete ·{" "}
                    {formatMinutes(roadmap.total_estimated_minutes)} total
                  </p>
                </div>
                <Link
                  to={`/analysis/${roadmap.analysis_id}`}
                  className="text-sm font-medium text-indigo-300 hover:text-indigo-200"
                >
                  View match result →
                </Link>
              </div>
              <div className="mt-4 h-3 w-full overflow-hidden rounded-full bg-white/5">
                <div
                  className="h-full rounded-full bg-emerald-400 transition-all"
                  style={{ width: `${roadmap.progress_percentage}%` }}
                />
              </div>
            </section>

            <section className="mt-6 rounded-2xl border border-white/10 bg-white/[0.03] p-6">
              <h2 className="text-lg font-semibold text-white">Why these skills</h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-300">{roadmap.summary}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {roadmap.priority_skills.map((skill, index) => (
                  <span
                    key={`${skill}-${index}`}
                    className="rounded-full border border-indigo-400/30 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-200"
                  >
                    {skill}
                  </span>
                ))}
              </div>
              <p className="mt-4 text-xs text-slate-500">
                {roadmap.generation_engine === "llm"
                  ? "AI generated the recommendations; the backend validated and stored them."
                  : "AI is not configured, so the local rule-based recommender was used."}
              </p>
            </section>

            {error && (
              <p className="mt-6 rounded-lg border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                {error}
              </p>
            )}

            <section className="mt-8 space-y-4">
              {roadmap.tasks.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  roadmapId={roadmap.id}
                  updating={updatingId !== null}
                  onToggle={handleToggle}
                />
              ))}
            </section>
          </>
        ) : null}
      </main>
      <Footer />
    </div>
  );
}
