import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import AuthShell from "../components/AuthShell";
import FormField from "../components/FormField";
import { useAuth } from "../context/AuthContext";
import { getApiErrorMessage } from "../lib/api";

export default function LoginPage() {
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (loading) {
    return (
      <AuthShell title="Checking session" subtitle="Loading your profile…">
        <p className="text-sm text-slate-400">Please wait…</p>
      </AuthShell>
    );
  }
  if (user) return <Navigate to="/profile" replace />;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login({ email, password });
      navigate("/profile", { replace: true });
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthShell title="Welcome back" subtitle="Log in to continue your placement prep.">
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {error && (
          <p className="rounded-lg border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
            {error}
          </p>
        )}
        <FormField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="you@college.edu"
        />
        <FormField
          id="password"
          label="Password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Enter your password"
        />
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-linear-to-r from-indigo-500 to-fuchsia-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? "Logging in…" : "Log in"}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-400">
        New here?{" "}
        <Link to="/register" className="font-semibold text-indigo-300 hover:text-indigo-200">
          Create an account
        </Link>
      </p>
    </AuthShell>
  );
}
