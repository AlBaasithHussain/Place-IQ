import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";

import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import {
  getApiErrorMessage,
  getDashboard,
  type DashboardData,
  type DashboardSkill,
  type PlacementReadiness,
  type ScoreTrendPoint,
  type TargetSkillFrequency,
} from "../lib/api";
import { formatDate } from "../lib/format";

function scoreClass(value: number): string {
  if (value >= 75) return "text-emerald-300";
  if (value >= 50) return "text-amber-300";
  return "text-rose-300";
}

function barClass(value: number): string {
  if (value >= 75) return "bg-emerald-400";
  if (value >= 50) return "bg-amber-400";
  return "bg-rose-400";
}

function strokeColor(value: number): string {
  if (value >= 75) return "#34d399";
  if (value >= 50) return "#fbbf24";
  return "#fb7185";
}

function clamp(value: number): number {
  return Math.max(0, Math.min(100, value));
}

function Panel({
  title,
  subtitle,
  action,
  children,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">{title}</h2>
          {subtitle && <p className="mt-1 text-sm text-slate-400">{subtitle}</p>}
        </div>
        {action}
      </div>
      <div className="mt-5">{children}</div>
    </section>
  );
}

function SectionTitle({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-xl font-semibold text-white sm:text-2xl">{title}</h2>
      <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
    </div>
  );
}

function ProgressBar({ value, label }: { value: number; label?: string }) {
  const normalized = clamp(value);
  return (
    <div>
      {label && (
        <div className="mb-2 flex items-center justify-between text-xs text-slate-400">
          <span>{label}</span>
          <span>{normalized}%</span>
        </div>
      )}
      <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
        <div
          className={`h-full rounded-full transition-all ${barClass(normalized)}`}
          style={{ width: `${normalized}%` }}
        />
      </div>
    </div>
  );
}

function DonutChart({ value, caption }: { value: number; caption: string }) {
  const normalized = clamp(value);
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - normalized / 100);

  return (
    <div className="flex items-center gap-4">
      <svg viewBox="0 0 100 100" className="h-24 w-24 shrink-0" aria-label={`${caption} ${normalized} percent`}>
        <circle cx="50" cy="50" r={radius} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="10" />
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke={strokeColor(normalized)}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 50 50)"
        />
        <text x="50" y="55" textAnchor="middle" className="fill-white text-[18px] font-bold">
          {normalized}
        </text>
      </svg>
      <div>
        <p className="text-sm font-medium text-slate-300">{caption}</p>
        <p className="mt-1 text-xs text-slate-500">Out of 100</p>
      </div>
    </div>
  );
}

function TrendChart({
  points,
  label,
  color,
}: {
  points: ScoreTrendPoint[];
  label: string;
  color: string;
}) {
  const width = 320;
  const height = 120;
  const padding = 14;
  const coordinates = points.map((point, index) => {
    const x = padding + (index * (width - padding * 2)) / Math.max(1, points.length - 1);
    const y = height - padding - (clamp(point.value) / 100) * (height - padding * 2);
    return { x, y, point };
  });
  const line = coordinates.map((item) => `${item.x},${item.y}`).join(" ");
  const first = coordinates[0];
  const last = coordinates[coordinates.length - 1];
  const area = first && last ? `${first.x},${height - padding} ${line} ${last.x},${height - padding}` : "";

  return (
    <div className="rounded-xl border border-white/10 bg-slate-950/40 p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-slate-300">{label}</p>
        <p className="text-xs text-slate-500">{points.length} data point{points.length === 1 ? "" : "s"}</p>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="mt-3 w-full" role="img" aria-label={`${label} trend chart`}>
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="rgba(255,255,255,0.12)" />
        <line x1={padding} y1={padding} x2={width - padding} y2={padding} stroke="rgba(255,255,255,0.06)" />
        {area && <polygon points={area} fill={color} opacity="0.12" />}
        {line && <polyline points={line} fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />}
        {coordinates.map((item, index) => (
          <circle key={`${item.point.label}-${index}`} cx={item.x} cy={item.y} r="3.5" fill={color} />
        ))}
      </svg>
      {points.length > 0 && (
        <div className="mt-1 flex justify-between text-[11px] text-slate-500">
          <span>{points[0].label}</span>
          <span>{points[points.length - 1].label}</span>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  suffix,
  subtitle,
  progress,
  link,
  linkLabel,
}: {
  label: string;
  value: string | number;
  suffix?: string;
  subtitle: string;
  progress?: number;
  link?: string;
  linkLabel?: string;
}) {
  return (
    <article className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{label}</p>
      <div className="mt-3 flex items-baseline gap-1">
        <span className={`text-3xl font-extrabold ${scoreClass(typeof value === "number" ? value : 100)}`}>
          {value}
        </span>
        {suffix && <span className="text-sm text-slate-500">{suffix}</span>}
      </div>
      <p className="mt-2 min-h-10 text-sm text-slate-400">{subtitle}</p>
      {progress !== undefined && (
        <div className="mt-4">
          <ProgressBar value={progress} />
        </div>
      )}
      {link && linkLabel && (
        <Link to={link} className="mt-4 inline-flex text-sm font-semibold text-indigo-300 transition hover:text-indigo-200">
          {linkLabel} →
        </Link>
      )}
    </article>
  );
}

function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] px-6 py-10 text-center">
      <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-slate-400">{description}</p>
      {action && <div className="mt-4 flex flex-wrap justify-center gap-3">{action}</div>}
    </div>
  );
}

function ActionLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link
      to={to}
      className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm font-semibold text-slate-200 transition hover:bg-white/10"
    >
      {children}
    </Link>
  );
}

function SkillSplitChart({ strong, partial, missing }: { strong: number; partial: number; missing: number }) {
  const rows = [
    { label: "Strong", value: strong, className: "bg-emerald-400" },
    { label: "Partial", value: partial, className: "bg-amber-400" },
    { label: "Missing", value: missing, className: "bg-rose-400" },
  ];
  const max = Math.max(1, strong, partial, missing);

  return (
    <div className="space-y-4">
      {rows.map((row) => (
        <div key={row.label}>
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="text-slate-300">{row.label}</span>
            <span className="font-semibold text-white">{row.value}</span>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-white/5">
            <div
              className={`h-full rounded-full ${row.className}`}
              style={{ width: `${(row.value / max) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function ReadinessPanel({ readiness }: { readiness: PlacementReadiness }) {
  return (
    <Panel
      title="Placement Readiness Score"
      subtitle={`${readiness.band} · deterministic weighted score`}
    >
      <div className="grid gap-8 lg:grid-cols-[minmax(220px,320px)_1fr]">
        <div className="flex flex-col items-center gap-4 sm:flex-row lg:flex-col">
          <DonutChart value={readiness.score} caption="Placement readiness" />
          <div className="w-full rounded-xl border border-white/10 bg-slate-950/40 p-4 text-center sm:text-left">
            <p className="text-xs uppercase tracking-wider text-slate-500">Readiness band</p>
            <p className="mt-2 text-lg font-semibold text-white">{readiness.band}</p>
          </div>
        </div>
        <div>
          <div className="space-y-4">
            {readiness.components.map((component) => (
              <div key={component.key}>
                <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
                  <span className="font-medium text-slate-300">
                    {component.label}
                    <span className="ml-2 text-xs text-slate-500">
                      {Math.round(component.weight * 100)}% weight
                    </span>
                  </span>
                  <span className="text-slate-400">
                    {component.score}/100 · {component.contribution} pts
                  </span>
                </div>
                <div className="mt-2">
                  <ProgressBar value={component.score} />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-6 rounded-xl border border-indigo-400/20 bg-indigo-500/[0.06] p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-indigo-200">
              Formula
            </p>
            <p className="mt-2 text-sm leading-relaxed text-slate-300">{readiness.formula}</p>
          </div>
        </div>
      </div>
    </Panel>
  );
}

function TargetSkillChart({
  skills,
  totalJobs,
}: {
  skills: TargetSkillFrequency[];
  totalJobs: number;
}) {
  return (
    <div className="space-y-5">
      {skills.map((skill) => (
        <div key={skill.skill}>
          <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
            <span className="font-medium text-slate-200">{skill.skill}</span>
            <span className={scoreClass(skill.frequency_percentage)}>
              {skill.job_count}/{totalJobs} jobs · {skill.frequency_percentage}%
            </span>
          </div>
          <div className="mt-2 h-3 w-full overflow-hidden rounded-full bg-white/5">
            <div
              className="h-full rounded-full bg-linear-to-r from-indigo-500 to-fuchsia-500"
              style={{ width: `${clamp(skill.frequency_percentage)}%` }}
            />
          </div>
          <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-500">
            <span>Required in {skill.required_count} jobs</span>
            <span>Preferred in {skill.preferred_count} jobs</span>
            <span className="capitalize">{skill.requirement_types.join(" · ") || "not specified"}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

type SkillTableRow = DashboardSkill & { status: "Strong" | "Partial" | "Missing" };

const STATUS_STYLE: Record<SkillTableRow["status"], string> = {
  Strong: "border-emerald-400/30 bg-emerald-500/10 text-emerald-200",
  Partial: "border-amber-400/30 bg-amber-500/10 text-amber-200",
  Missing: "border-rose-400/30 bg-rose-500/10 text-rose-200",
};

function SkillTable({ rows }: { rows: SkillTableRow[] }) {
  return (
    <div className="mt-6 overflow-x-auto">
      <table className="w-full min-w-[420px] text-left text-sm">
        <thead className="text-xs uppercase tracking-wider text-slate-500">
          <tr>
            <th className="pb-3 font-semibold">Skill</th>
            <th className="pb-3 font-semibold">Status</th>
            <th className="pb-3 font-semibold">Requirement</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {rows.map((row, index) => (
            <tr key={`${row.skill}-${index}`}>
              <td className="py-3 pr-4 font-medium text-slate-200">{row.skill}</td>
              <td className="py-3 pr-4">
                <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[row.status]}`}>
                  {row.status}
                </span>
              </td>
              <td className="py-3 text-slate-400">{row.requirement_type ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function LoadingDashboard() {
  return (
    <div className="space-y-6">
      <div className="h-10 w-64 animate-pulse rounded-lg bg-white/10" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((item) => (
          <div key={item} className="h-40 animate-pulse rounded-2xl border border-white/10 bg-white/[0.03]" />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-2">
        <div className="h-80 animate-pulse rounded-2xl border border-white/10 bg-white/[0.03]" />
        <div className="h-80 animate-pulse rounded-2xl border border-white/10 bg-white/[0.03]" />
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getDashboard());
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const skillRows: SkillTableRow[] = data
    ? [
        ...data.skill_analysis.strong_skills.map((item) => ({ ...item, status: "Strong" as const })),
        ...data.skill_analysis.partial_skills.map((item) => ({ ...item, status: "Partial" as const })),
        ...data.skill_analysis.missing_skills.map((item) => ({ ...item, status: "Missing" as const })),
      ]
    : [];

  return (
    <div className="min-h-screen bg-slate-950 font-sans text-slate-100">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-12">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-widest text-indigo-300">Student dashboard</p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight text-white sm:text-4xl">
              {user
                ? `Welcome back, ${user.name?.split(" ")[0] || user.email}`
                : "Your preparation at a glance"}
            </h1>
            <p className="mt-2 text-sm text-slate-400">
              Track resumes, matches, learning and interview readiness in one place.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => void load()}
              disabled={loading}
              className="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:bg-white/10 disabled:opacity-50"
            >
              {loading ? "Refreshing..." : "Refresh"}
            </button>
            <ActionLink to="/analysis/new">New match</ActionLink>
          </div>
        </div>

        {loading && <LoadingDashboard />}

        {!loading && error && (
          <div className="rounded-xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            <p className="font-semibold">Could not load the dashboard</p>
            <p className="mt-1 text-rose-200/80">{error}</p>
            <button
              type="button"
              onClick={() => void load()}
              className="mt-3 rounded-lg border border-rose-300/30 bg-rose-500/10 px-3 py-2 text-sm font-semibold text-rose-100 transition hover:bg-rose-500/20"
            >
              Try again
            </button>
          </div>
        )}

        {!loading && !error && data && (
          <div className="space-y-10">
            {!data.has_data && (
              <EmptyState
                title="Your dashboard is ready"
                description="Upload a resume and analyze a job description to start building your preparation history."
                action={
                  <>
                    <ActionLink to="/resumes">Upload resume</ActionLink>
                    <ActionLink to="/jobs">Analyze a job</ActionLink>
                    <ActionLink to="/roadmaps/new">Create roadmap</ActionLink>
                  </>
                }
              />
            )}

            <section>
              <SectionTitle
                title="Placement Readiness"
                subtitle="A transparent, weighted score built from your saved preparation data."
              />
              <ReadinessPanel readiness={data.readiness} />
            </section>

            <section>
              <SectionTitle title="Overview" subtitle="Your key placement readiness indicators." />
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <StatCard
                  label="Resume Score"
                  value={data.overview.resume_score}
                  suffix="/100"
                  subtitle={data.overview.resume_file_name ?? "No resume uploaded yet"}
                  progress={data.overview.resume_score}
                  link={data.overview.resume_file_name ? "/resumes" : undefined}
                  linkLabel="View resumes"
                />
                <StatCard
                  label="Job Match Score"
                  value={data.overview.job_match_score}
                  suffix="/100"
                  subtitle={data.overview.latest_analysis_id ? "From your latest job match" : "Run a job match to see this"}
                  progress={data.overview.job_match_score}
                  link={data.overview.latest_analysis_id ? `/analysis/${data.overview.latest_analysis_id}` : undefined}
                  linkLabel="View match"
                />
                <StatCard
                  label="Interview Score"
                  value={data.overview.interview_score}
                  suffix="/100"
                  subtitle={data.overview.latest_interview_id ? "From your latest evaluation" : "Evaluate an interview to see this"}
                  progress={data.overview.interview_score}
                  link={data.overview.latest_interview_id ? `/interviews/${data.overview.latest_interview_id}/results` : undefined}
                  linkLabel="View results"
                />
                <StatCard
                  label="Skills Learned"
                  value={data.overview.skills_learned}
                  subtitle={
                    data.overview.learned_skills.length > 0
                      ? data.overview.learned_skills.slice(0, 3).join(", ")
                      : "Complete roadmap tasks to learn skills"
                  }
                  progress={Math.min(100, data.overview.skills_learned * 5)}
                />
              </div>

              <div className="mt-6">
                <Panel title="Score trends" subtitle="Recent match and interview evaluation scores.">
                  <div className="grid gap-4 lg:grid-cols-2">
                    {data.trends.match_scores.length > 0 ? (
                      <TrendChart points={data.trends.match_scores} label="Job match score" color="#818cf8" />
                    ) : (
                      <EmptyState title="No match trend yet" description="Analyze a job against your resume to start tracking match scores." />
                    )}
                    {data.trends.interview_scores.length > 0 ? (
                      <TrendChart points={data.trends.interview_scores} label="Interview score" color="#34d399" />
                    ) : (
                      <EmptyState title="No interview trend yet" description="Complete and evaluate a mock interview to track your scores." />
                    )}
                  </div>
                </Panel>
              </div>
            </section>

            <section>
              <SectionTitle
                title="Top Skills Needed Across My Target Jobs"
                subtitle="Skills requested most often across every job description you analyzed."
              />
              <Panel
                title="Target skill frequency"
                subtitle={`${data.target_skills.total_jobs} job${data.target_skills.total_jobs === 1 ? "" : "s"} analyzed`}
                action={<ActionLink to="/jobs">Analyze jobs</ActionLink>}
              >
                {data.target_skills.skills.length === 0 ? (
                  <EmptyState
                    title="No target skills yet"
                    description="Analyze multiple job descriptions to see which skills are requested most often."
                    action={<ActionLink to="/jobs">Analyze a job</ActionLink>}
                  />
                ) : (
                  <TargetSkillChart
                    skills={data.target_skills.skills}
                    totalJobs={data.target_skills.total_jobs}
                  />
                )}
              </Panel>
            </section>

            <section>
              <SectionTitle title="Skill analysis" subtitle="Based on your latest resume and job match." />
              <Panel
                title="Skill breakdown"
                subtitle={data.skill_analysis.job_title ?? "No job match selected"}
                action={
                  data.skill_analysis.analysis_id ? (
                    <ActionLink to={`/analysis/${data.skill_analysis.analysis_id}`}>Open analysis</ActionLink>
                  ) : undefined
                }
              >
                {skillRows.length === 0 ? (
                  <EmptyState
                    title="No skill comparison yet"
                    description="Match a resume with a job description to see strong, partial and missing skills."
                    action={<ActionLink to="/analysis/new">Start a match</ActionLink>}
                  />
                ) : (
                  <div className="grid gap-8 lg:grid-cols-[minmax(220px,320px)_1fr]">
                    <SkillSplitChart
                      strong={data.skill_analysis.strong_skills.length}
                      partial={data.skill_analysis.partial_skills.length}
                      missing={data.skill_analysis.missing_skills.length}
                    />
                    <SkillTable rows={skillRows} />
                  </div>
                )}
              </Panel>
            </section>

            <div className="grid gap-6 xl:grid-cols-2">
              <section>
                <SectionTitle title="Learning progress" subtitle="Daily tasks from your latest 7-day roadmap." />
                <Panel
                  title={data.learning_progress.has_roadmap ? `${data.learning_progress.duration_days}-Day Roadmap` : "7-Day Roadmap"}
                  subtitle={data.learning_progress.job_title ?? "No roadmap generated yet"}
                  action={
                    data.learning_progress.roadmap_id ? (
                      <ActionLink to={`/roadmaps/${data.learning_progress.roadmap_id}`}>Open roadmap</ActionLink>
                    ) : undefined
                  }
                >
                  {!data.learning_progress.has_roadmap ? (
                    <EmptyState
                      title="No 7-day roadmap yet"
                      description="Generate a 7-day plan from a job match to track completed and remaining tasks."
                      action={<ActionLink to="/roadmaps/new">Generate roadmap</ActionLink>}
                    />
                  ) : (
                    <div className="space-y-6">
                      <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
                        <DonutChart
                          value={data.learning_progress.progress_percentage}
                          caption="Roadmap complete"
                        />
                        <div className="flex-1">
                          <ProgressBar value={data.learning_progress.progress_percentage} label="Overall progress" />
                          <p className="mt-3 text-sm leading-relaxed text-slate-400">
                            {data.learning_progress.summary || "Your daily study plan is ready."}
                          </p>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="rounded-xl border border-emerald-400/20 bg-emerald-500/[0.06] p-4">
                          <p className="text-xs uppercase tracking-wider text-emerald-200/70">Completed tasks</p>
                          <p className="mt-2 text-2xl font-bold text-emerald-200">{data.learning_progress.completed_tasks}</p>
                        </div>
                        <div className="rounded-xl border border-amber-400/20 bg-amber-500/[0.06] p-4">
                          <p className="text-xs uppercase tracking-wider text-amber-200/70">Remaining tasks</p>
                          <p className="mt-2 text-2xl font-bold text-amber-200">{data.learning_progress.remaining_tasks}</p>
                        </div>
                      </div>
                      {data.learning_progress.priority_skills.length > 0 && (
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Priority skills</p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {data.learning_progress.priority_skills.map((skill, index) => (
                              <span
                                key={`${skill}-${index}`}
                                className="rounded-full border border-indigo-400/20 bg-indigo-500/10 px-3 py-1 text-xs text-indigo-200"
                              >
                                {skill}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </Panel>
              </section>

              <section>
                <SectionTitle title="Interview" subtitle="Practice volume and evaluation performance." />
                <Panel title="Interview readiness" subtitle="Across all of your mock interview sessions.">
                  <div className="grid gap-3 sm:grid-cols-3">
                    <div className="rounded-xl border border-white/10 bg-slate-950/40 p-4">
                      <p className="text-xs uppercase tracking-wider text-slate-500">Questions Attempted</p>
                      <p className="mt-2 text-2xl font-bold text-white">
                        {data.interview.questions_attempted}
                        <span className="text-sm font-normal text-slate-500">/{data.interview.questions_total}</span>
                      </p>
                    </div>
                    <div className="rounded-xl border border-white/10 bg-slate-950/40 p-4">
                      <p className="text-xs uppercase tracking-wider text-slate-500">Average Score</p>
                      <p className={`mt-2 text-2xl font-bold ${scoreClass(data.interview.average_score)}`}>
                        {data.interview.average_score}
                      </p>
                    </div>
                    <div className="rounded-xl border border-white/10 bg-slate-950/40 p-4">
                      <p className="text-xs uppercase tracking-wider text-slate-500">Latest Score</p>
                      <p className={`mt-2 text-2xl font-bold ${scoreClass(data.interview.latest_score)}`}>
                        {data.interview.latest_score}
                      </p>
                    </div>
                  </div>
                  <div className="mt-5 rounded-xl border border-white/10 bg-white/[0.02] p-4 text-sm text-slate-400">
                    <div className="flex flex-wrap gap-x-6 gap-y-2">
                      <span>{data.interview.sessions} session{data.interview.sessions === 1 ? "" : "s"}</span>
                      <span>{data.interview.completed_sessions} completed</span>
                      <span>{data.interview.evaluated_sessions} evaluated</span>
                    </div>
                  </div>
                  <div className="mt-5">
                    {data.trends.interview_scores.length > 0 ? (
                      <TrendChart points={data.trends.interview_scores} label="Interview scores" color="#34d399" />
                    ) : (
                      <EmptyState
                        title="No interview scores yet"
                        description="Answer all questions in a mock interview, then evaluate your responses."
                        action={<ActionLink to="/interviews/start">Start an interview</ActionLink>}
                      />
                    )}
                  </div>
                </Panel>
              </section>
            </div>

            <section>
              <SectionTitle title="Job analysis" subtitle="Your most recently analyzed job descriptions." />
              <Panel title="Recently analyzed jobs" subtitle="Newest first, with the latest saved match score.">
                {data.recent_jobs.length === 0 ? (
                  <EmptyState
                    title="No jobs analyzed yet"
                    description="Paste a job description to extract skills and requirements for matching."
                    action={<ActionLink to="/jobs">Analyze a job</ActionLink>}
                  />
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[560px] text-left text-sm">
                      <thead className="text-xs uppercase tracking-wider text-slate-500">
                        <tr>
                          <th className="pb-3 font-semibold">Job</th>
                          <th className="pb-3 font-semibold">Engine</th>
                          <th className="pb-3 font-semibold">Analyzed</th>
                          <th className="pb-3 font-semibold">Match</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {data.recent_jobs.map((job) => (
                          <tr key={job.id} className="transition hover:bg-white/[0.02]">
                            <td className="py-3 pr-4">
                              <Link to={`/jobs/${job.id}`} className="font-medium text-slate-200 hover:text-white">
                                {job.job_title}
                              </Link>
                            </td>
                            <td className="py-3 pr-4">
                              <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-xs capitalize text-slate-300">
                                {job.analysis_engine}
                              </span>
                            </td>
                            <td className="py-3 pr-4 text-slate-400">{formatDate(job.created_at)}</td>
                            <td className="py-3">
                              {job.match_score === null ? (
                                <span className="text-slate-500">Not matched</span>
                              ) : (
                                <span className={`font-semibold ${scoreClass(job.match_score)}`}>
                                  {job.match_score}/100
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Panel>
            </section>
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
