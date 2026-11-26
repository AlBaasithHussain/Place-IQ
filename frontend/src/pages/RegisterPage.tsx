import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import AuthShell from "../components/AuthShell";
import FormField from "../components/FormField";
import { useAuth } from "../context/AuthContext";
import { getApiErrorMessage } from "../lib/api";

export default function RegisterPage() {
  const { user, loading, register } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
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

  function validate(): string | null {
    if (password.length < 8) return "Password must be at least 8 characters.";
    if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      return "Password must contain at least one letter and one number.";
    }
    if (password !== confirm) return "Passwords do not match.";
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await register({ name, email, password });
      navigate("/profile", { replace: true });
    } catch (err) {
      setError(getApiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthShell title="Create your account" subtitle="Start finding your skill gaps in minutes.">
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {error && (
          <p className="rounded-lg border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
            {error}
          </p>
        )}
        <FormField
          id="name"
          label="Full name"
          type="text"
          autoComplete="name"
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Asha Verma"
        />
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
          autoComplete="new-password"
          required
          minLength={8}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="At least 8 characters"
        />
        <FormField
          id="confirm"
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          required
          value={confirm}
          onChange={(event) => setConfirm(event.target.value)}
          placeholder="Re-enter your password"
        />
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-linear-to-r from-indigo-500 to-fuchsia-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? "Creating account…" : "Create account"}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-400">
        Already have an account?{" "}
        <Link to="/login" className="font-semibold text-indigo-300 hover:text-indigo-200">
          Log in
        </Link>
      </p>
    </AuthShell>
  );
}
