import { useEffect, useState } from "react";

import { fetchHealth } from "../lib/api";

type Status = "loading" | "online" | "offline";

const styles: Record<Status, { dot: string; text: string; label: string }> = {
  loading: {
    dot: "bg-amber-400 animate-pulse",
    text: "text-amber-200/90",
    label: "Connecting to API…",
  },
  online: {
    dot: "bg-emerald-400",
    text: "text-emerald-200/90",
    label: "API online",
  },
  offline: {
    dot: "bg-rose-400",
    text: "text-rose-200/90",
    label: "API offline — start the backend",
  },
};

export default function StatusBadge() {
  const [status, setStatus] = useState<Status>("loading");
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    fetchHealth()
      .then((health) => {
        if (!active) return;
        setVersion(health.version);
        setStatus("online");
      })
      .catch(() => {
        if (active) setStatus("offline");
      });

    return () => {
      active = false;
    };
  }, []);

  const s = styles[status];
  const label = status === "online" && version ? `${s.label} · v${version}` : s.label;

  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium backdrop-blur">
      <span className={`h-2 w-2 rounded-full ${s.dot}`} />
      <span className={s.text}>{label}</span>
    </span>
  );
}
