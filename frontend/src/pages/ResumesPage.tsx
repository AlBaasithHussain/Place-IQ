import { useEffect, useState, type ChangeEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import {
  getApiErrorMessage,
  listResumes,
  uploadResume,
  type ResumeSummary,
} from "../lib/api";
import { formatBytes, formatDate } from "../lib/format";

const MAX_BYTES = 5 * 1024 * 1024;

export default function ResumesPage() {
  const navigate = useNavigate();

  const [resumes, setResumes] = useState<ResumeSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selected, setSelected] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    listResumes()
      .then((data) => {
        if (active) setResumes(data);
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

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setError(null);

    if (!file) {
      setSelected(null);
      return;
    }
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setSelected(null);
      setError("Please choose a PDF file.");
      return;
    }
    if (file.type && file.type !== "application/pdf") {
      setSelected(null);
      setError("Please choose a PDF file.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setSelected(null);
      setError("File is too large (maximum is 5 MB).");
      return;
    }
    setSelected(file);
  }

  async function handleUpload() {
    if (!selected) {
      setError("Choose a PDF resume to upload.");
      return;
    }
    setUploading(true);
    setError(null);
    try {
      const resume = await uploadResume(selected);
      navigate(`/resumes/${resume.id}`);
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 font-sans text-slate-100">
      <Navbar />
      <main className="mx-auto max-w-5xl px-6 py-12">
        <h1 className="text-3xl font-bold tracking-tight text-white">Resumes</h1>
        <p className="mt-2 text-slate-400">
          Upload a PDF resume and we&apos;ll pull out your skills, projects and education.
        </p>

        <section className="mt-8 rounded-2xl border border-white/10 bg-white/[0.03] p-6">
          <h2 className="text-lg font-semibold text-white">Upload a resume</h2>
          <p className="mt-1 text-sm text-slate-400">Text-based PDF, up to 5 MB.</p>

          {error && (
            <p className="mt-4 rounded-lg border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
              {error}
            </p>
          )}

          <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-center">
            <input
              type="file"
              accept="application/pdf,.pdf"
              onChange={handleFileChange}
              className="block w-full cursor-pointer text-sm text-slate-300 file:mr-4 file:cursor-pointer file:rounded-lg file:border-0 file:bg-white/10 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-slate-100 hover:file:bg-white/20"
            />
            <button
              onClick={handleUpload}
              disabled={uploading || !selected}
              className="shrink-0 rounded-lg bg-linear-to-r from-indigo-500 to-fuchsia-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {uploading ? "Uploading…" : "Upload & analyze"}
            </button>
          </div>
        </section>

        <section className="mt-8">
          <h2 className="text-lg font-semibold text-white">Your resumes</h2>

          {loading ? (
            <p className="mt-4 animate-pulse text-sm text-slate-400">Loading resumes…</p>
          ) : resumes.length === 0 ? (
            <p className="mt-4 rounded-2xl border border-dashed border-white/10 bg-white/[0.02] px-6 py-10 text-center text-sm text-slate-400">
              No resumes yet. Upload your first PDF above.
            </p>
          ) : (
            <ul className="mt-4 space-y-3">
              {resumes.map((resume) => (
                <li key={resume.id}>
                  <Link
                    to={`/resumes/${resume.id}`}
                    className="block rounded-xl border border-white/10 bg-white/[0.03] px-5 py-4 transition hover:border-indigo-400/40 hover:bg-white/[0.05]"
                  >
                    <div className="flex items-center justify-between gap-4">
                      <div className="min-w-0">
                        <p className="truncate font-semibold text-white">
                          {resume.name ?? resume.original_filename}
                        </p>
                        <p className="truncate text-sm text-slate-400">
                          {resume.email ?? "No email detected"} · {resume.original_filename}
                        </p>
                      </div>
                      <div className="shrink-0 text-right text-xs text-slate-500">
                        <p>{formatBytes(resume.file_size)}</p>
                        <p>{formatDate(resume.created_at)}</p>
                      </div>
                    </div>
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
