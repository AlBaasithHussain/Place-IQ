export default function Footer() {
  return (
    <footer className="border-t border-white/5">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 py-8 text-sm text-slate-400 sm:flex-row">
        <div className="flex items-center gap-2">
          <span className="grid h-7 w-7 place-items-center rounded-md bg-linear-to-br from-indigo-500 to-fuchsia-500 text-xs font-extrabold text-white">
            P
          </span>
          <span className="font-semibold text-slate-200">PrepPilot</span>
        </div>
        <p>AI-Powered Placement Preparation &amp; Skill Gap Analyzer</p>
        <p className="text-slate-500">© {new Date().getFullYear()} PrepPilot</p>
      </div>
    </footer>
  );
}
