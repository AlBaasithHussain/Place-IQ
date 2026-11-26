import { useEffect, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import TagList from "../components/TagList";
import { getApiErrorMessage, getResume, type ResumeDetail } from "../lib/api";
import { formatBytes, formatDate } from "../lib/format";

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

export default function ResumeDetailPage() {
  const { id } = useParams<{ id: string }>();

  const [resume, setResume] = useState<ResumeDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const numericId = Number(id);
    if (!Number.isInteger(numericId) || numericId <= 0) {
      setError("Invalid resume id.");
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    getResume(numericId)
      .then((data) => {
        if (active) setResume(data);
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

  const parsed = resume?.parsed_data;

  return (
    <div className="min-h-screen bg-slate-950 font-sans text-slate-100">
      <Navbar />
      <main className="mx-auto max-w-5xl px-6 py-12">
        <Link
          to="/resumes"
          className="text-sm font-medium text-indigo-300 transition hover:text-indigo-200"
        >
          ← Back to resumes
        </Link>

        {loading ? (
          <p className="mt-6 animate-pulse text-sm text-slate-400">Loading resume…</p>
        ) : error ? (
          <p className="mt-6 rounded-lg border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </p>
        ) : resume && parsed ? (
          <>
            <header className="mt-4 flex flex-wrap items-end justify-between gap-4">
              <div className="min-w-0">
                <h1 className="truncate text-3xl font-bold tracking-tight text-white">
                  {parsed.name ?? resume.original_filename}
                </h1>
                <p className="mt-1 text-slate-400">
                  {parsed.email ?? "No email detected"} · {resume.original_filename} ·{" "}
                  {formatBytes(resume.file_size)} · {formatDate(resume.created_at)}
                </p>
              </div>
            </header>

            <div className="mt-8 grid gap-6 lg:grid-cols-2">
              <Panel title="Skills">
                <TagList items={parsed.skills} />
              </Panel>
              <Panel title="Contact & identity">
                <dl className="space-y-2 text-sm">
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-400">Name</dt>
                    <dd className="text-right text-slate-200">
                      {parsed.name ?? "Not detected"}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-400">Email</dt>
                    <dd className="text-right text-slate-200">
                      {parsed.email ?? "Not detected"}
                    </dd>
                  </div>
                </dl>
              </Panel>

              <Panel title="Programming languages">
                <TagList items={parsed.programming_languages} />
              </Panel>
              <Panel title="Frameworks & libraries">
                <TagList items={parsed.frameworks} />
              </Panel>
              <Panel title="Databases">
                <TagList items={parsed.databases} />
              </Panel>
              <Panel title="Tools & platforms">
                <TagList items={parsed.tools} />
              </Panel>

              <Panel title="Education">
                <BulletList items={parsed.education} />
              </Panel>
              <Panel title="Experience">
                <BulletList items={parsed.experience} />
              </Panel>
              <Panel title="Projects">
                <BulletList items={parsed.projects} />
              </Panel>
              <Panel title="Certifications">
                <BulletList items={parsed.certifications} />
              </Panel>
            </div>

            <details className="mt-6 rounded-2xl border border-white/10 bg-white/[0.03] p-6">
              <summary className="cursor-pointer text-sm font-semibold text-slate-300">
                Extracted text
              </summary>
              <pre className="mt-4 max-h-80 overflow-auto whitespace-pre-wrap text-xs leading-relaxed text-slate-400">
                {resume.raw_text}
              </pre>
            </details>
          </>
        ) : null}
      </main>
      <Footer />
    </div>
  );
}
