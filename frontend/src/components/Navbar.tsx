import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/");
  }

  return (
    <header className="sticky top-0 z-50 border-b border-white/5 bg-slate-950/70 backdrop-blur-xl">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link to="/" className="flex items-center gap-2">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-linear-to-br from-indigo-500 to-fuchsia-500 text-sm font-extrabold text-white">
            P
          </span>
          <span className="text-lg font-bold tracking-tight text-white">PrepPilot</span>
        </Link>

        <div className="hidden items-center gap-8 text-sm font-medium text-slate-300 md:flex">
          <a href="/#features" className="transition hover:text-white">
            Features
          </a>
          <a href="/#how" className="transition hover:text-white">
            How it works
          </a>
          <a href="/#roadmap" className="transition hover:text-white">
            Roadmap
          </a>
        </div>

        <div className="flex items-center gap-3">
          {user ? (
            <>
              <Link
                to="/dashboard"
                className="hidden text-sm font-medium text-slate-300 transition hover:text-white sm:inline"
              >
                Dashboard
              </Link>
              <Link
                to="/analysis/new"
                className="hidden text-sm font-medium text-slate-300 transition hover:text-white sm:inline"
              >
                Match
              </Link>
              <Link
                to="/roadmaps/new"
                className="hidden text-sm font-medium text-slate-300 transition hover:text-white sm:inline"
              >
                Roadmap
              </Link>
              <Link
                to="/interviews/start"
                className="hidden text-sm font-medium text-slate-300 transition hover:text-white sm:inline"
              >
                Interview
              </Link>
              <Link
                to="/jobs"
                className="hidden text-sm font-medium text-slate-300 transition hover:text-white sm:inline"
              >
                Jobs
              </Link>
              <Link
                to="/resumes"
                className="hidden text-sm font-medium text-slate-300 transition hover:text-white sm:inline"
              >
                Resumes
              </Link>
              <Link
                to="/profile"
                className="hidden text-sm font-medium text-slate-300 transition hover:text-white sm:inline"
              >
                Profile
              </Link>
              <button
                onClick={handleLogout}
                className="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:bg-white/10"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link
                to="/login"
                className="text-sm font-medium text-slate-300 transition hover:text-white"
              >
                Log in
              </Link>
              <Link
                to="/register"
                className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-slate-900 transition hover:bg-slate-200"
              >
                Get started
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
