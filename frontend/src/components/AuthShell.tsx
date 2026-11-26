import type { ReactNode } from "react";

import Footer from "./Footer";
import Navbar from "./Navbar";

interface AuthShellProps {
  title: string;
  subtitle: string;
  children: ReactNode;
}

export default function AuthShell({ title, subtitle, children }: AuthShellProps) {
  return (
    <div className="min-h-screen bg-slate-950 font-sans text-slate-100">
      <Navbar />
      <main className="mx-auto flex w-full max-w-md flex-col justify-center px-6 py-16">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-8 shadow-2xl shadow-indigo-950/30">
          <h1 className="text-2xl font-bold tracking-tight text-white">{title}</h1>
          <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
          <div className="mt-6">{children}</div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
