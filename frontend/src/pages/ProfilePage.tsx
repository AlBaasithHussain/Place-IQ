import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import Footer from "../components/Footer";
import FormField from "../components/FormField";
import Navbar from "../components/Navbar";
import { useAuth } from "../context/AuthContext";
import {
  getApiErrorMessage,
  getProfile,
  updateProfile,
  type ProfileInput,
  type StudentProfile,
} from "../lib/api";

interface ProfileFormState {
  college: string;
  degree: string;
  branch: string;
  graduation_year: string;
  target_role: string;
}

const EMPTY_FORM: ProfileFormState = {
  college: "",
  degree: "",
  branch: "",
  graduation_year: "",
  target_role: "",
};

function profileToForm(profile: StudentProfile): ProfileFormState {
  return {
    college: profile.college ?? "",
    degree: profile.degree ?? "",
    branch: profile.branch ?? "",
    graduation_year: profile.graduation_year ? String(profile.graduation_year) : "",
    target_role: profile.target_role ?? "",
  };
}

function blankToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

function initialsOf(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export default function ProfilePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState<ProfileFormState>(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    getProfile()
      .then((profile) => {
        if (active) setForm(profileToForm(profile));
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

  if (!user) return null;

  function updateField(field: keyof ProfileFormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    const yearText = form.graduation_year.trim();
    let graduationYear: number | null = null;
    if (yearText !== "") {
      const parsed = Number(yearText);
      if (!Number.isInteger(parsed) || parsed < 1950 || parsed > 2100) {
        setError("Graduation year must be a whole number between 1950 and 2100.");
        return;
      }
      graduationYear = parsed;
    }

    const payload: ProfileInput = {
      college: blankToNull(form.college),
      degree: blankToNull(form.degree),
      branch: blankToNull(form.branch),
      graduation_year: graduationYear,
      target_role: blankToNull(form.target_role),
    };

    setSaving(true);
    try {
      const saved = await updateProfile(payload);
      setForm(profileToForm(saved));
      setSuccess("Profile saved.");
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleLogout() {
    await logout();
    navigate("/");
  }

  return (
    <div className="min-h-screen bg-slate-950 font-sans text-slate-100">
      <Navbar />
      <main className="mx-auto max-w-5xl px-6 py-12">
        <h1 className="text-3xl font-bold tracking-tight text-white">Your profile</h1>
        <p className="mt-2 text-slate-400">
          Keep your details up to date — they power your skill-gap analysis.
        </p>

        <div className="mt-8 grid gap-6 lg:grid-cols-3">
          <aside className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 lg:col-span-1">
            <div className="flex items-center gap-4">
              <span className="grid h-14 w-14 place-items-center rounded-full bg-linear-to-br from-indigo-500 to-fuchsia-500 text-lg font-extrabold text-white">
                {initialsOf(user.name)}
              </span>
              <div className="min-w-0">
                <p className="truncate font-semibold text-white">{user.name}</p>
                <p className="truncate text-sm text-slate-400">{user.email}</p>
              </div>
            </div>
            <dl className="mt-6 space-y-3 text-sm">
              <div className="flex justify-between gap-3">
                <dt className="text-slate-400">Member since</dt>
                <dd className="text-slate-200">
                  {new Date(user.created_at).toLocaleDateString()}
                </dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-slate-400">Account ID</dt>
                <dd className="text-slate-200">#{user.id}</dd>
              </div>
            </dl>
            <button
              onClick={handleLogout}
              className="mt-6 w-full rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:bg-white/10"
            >
              Log out
            </button>
          </aside>

          <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 lg:col-span-2">
            <h2 className="text-lg font-semibold text-white">Academic details</h2>
            <p className="mt-1 text-sm text-slate-400">
              These fields help us tailor recommendations to your goals.
            </p>

            {loading ? (
              <p className="mt-8 animate-pulse text-sm text-slate-400">Loading profile…</p>
            ) : (
              <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
                {error && (
                  <p className="rounded-lg border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
                    {error}
                  </p>
                )}
                {success && (
                  <p className="rounded-lg border border-emerald-400/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
                    {success}
                  </p>
                )}

                <div className="grid gap-4 sm:grid-cols-2">
                  <FormField
                    id="college"
                    label="College"
                    type="text"
                    value={form.college}
                    onChange={(event) => updateField("college", event.target.value)}
                    placeholder="e.g. NIT Trichy"
                  />
                  <FormField
                    id="degree"
                    label="Degree"
                    type="text"
                    value={form.degree}
                    onChange={(event) => updateField("degree", event.target.value)}
                    placeholder="e.g. B.Tech"
                  />
                  <FormField
                    id="branch"
                    label="Branch"
                    type="text"
                    value={form.branch}
                    onChange={(event) => updateField("branch", event.target.value)}
                    placeholder="e.g. Computer Science"
                  />
                  <FormField
                    id="graduation_year"
                    label="Graduation year"
                    type="number"
                    min={1950}
                    max={2100}
                    value={form.graduation_year}
                    onChange={(event) => updateField("graduation_year", event.target.value)}
                    placeholder="e.g. 2026"
                  />
                </div>

                <FormField
                  id="target_role"
                  label="Target role"
                  type="text"
                  value={form.target_role}
                  onChange={(event) => updateField("target_role", event.target.value)}
                  placeholder="e.g. Backend Engineer"
                />

                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-lg bg-linear-to-r from-indigo-500 to-fuchsia-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {saving ? "Saving…" : "Save profile"}
                </button>
              </form>
            )}
          </section>
        </div>
      </main>
      <Footer />
    </div>
  );
}
