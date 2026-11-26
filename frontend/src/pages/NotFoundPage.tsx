import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="grid min-h-screen place-items-center bg-slate-950 px-6 text-center font-sans text-slate-100">
      <div>
        <p className="text-sm font-semibold text-indigo-400">404</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">Page not found</h1>
        <p className="mt-2 text-slate-400">The page you are looking for does not exist.</p>
        <Link
          to="/"
          className="mt-6 inline-block rounded-lg bg-white px-5 py-2.5 text-sm font-semibold text-slate-900 transition hover:bg-slate-200"
        >
          Back home
        </Link>
      </div>
    </div>
  );
}
