"use client";

import { MODULE_INFO } from "@/lib/modules";

interface Props {
  name: string;
  active: boolean;
  loading?: boolean;
  onToggle: (name: string) => void;
}

const COLOR_MAP: Record<string, { icon: string; iconBg: string; badge: string; badgeBg: string }> = {
  blue:    { icon: "text-blue-600",    iconBg: "bg-blue-50",    badge: "text-blue-700",    badgeBg: "bg-blue-50" },
  purple:  { icon: "text-purple-600",  iconBg: "bg-purple-50",  badge: "text-purple-700",  badgeBg: "bg-purple-50" },
  orange:  { icon: "text-orange-600",  iconBg: "bg-orange-50",  badge: "text-orange-700",  badgeBg: "bg-orange-50" },
  emerald: { icon: "text-emerald-600", iconBg: "bg-emerald-50", badge: "text-emerald-700", badgeBg: "bg-emerald-50" },
  pink:    { icon: "text-pink-600",    iconBg: "bg-pink-50",    badge: "text-pink-700",    badgeBg: "bg-pink-50" },
  cyan:    { icon: "text-cyan-600",    iconBg: "bg-cyan-50",    badge: "text-cyan-700",    badgeBg: "bg-cyan-50" },
  amber:   { icon: "text-amber-600",   iconBg: "bg-amber-50",   badge: "text-amber-700",   badgeBg: "bg-amber-50" },
};

function ModuleIcon({ icon, className = "w-[18px] h-[18px]" }: { icon: string; className?: string }) {
  const icons: Record<string, JSX.Element> = {
    code: (
      <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5" />
      </svg>
    ),
    shield: (
      <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
      </svg>
    ),
    rss: (
      <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12.75 19.5v-.75a7.5 7.5 0 0 0-7.5-7.5H4.5m0 0v-.75a11.25 11.25 0 0 1 11.25-11.25h.75m-12 12h.008v.008H4.5v-.008Zm0 0a1.125 1.125 0 1 0 0 2.25 1.125 1.125 0 0 0 0-2.25Z" />
      </svg>
    ),
    chart: (
      <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
      </svg>
    ),
    brain: (
      <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
      </svg>
    ),
    chat: (
      <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 0 1-.825-.242m9.345-8.334a2.126 2.126 0 0 0-.476-.095 48.64 48.64 0 0 0-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0 0 11.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
      </svg>
    ),
    star: (
      <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z" />
      </svg>
    ),
  };
  return icons[icon] || null;
}

export default function ModuleCard({ name, active, loading, onToggle }: Props) {
  const info = MODULE_INFO[name] || {
    label: name,
    description: "Keine Beschreibung verfügbar.",
    icon: "code",
    color: "blue",
  };

  const colors = COLOR_MAP[info.color] || COLOR_MAP.blue;

  return (
    <div
      className={`rounded-xl border p-4 transition-all duration-200 card-shadow ${
        active
          ? "border-[var(--accent)]/20 bg-white ring-1 ring-[var(--accent)]/10"
          : "border-[var(--border)] bg-white hover:border-[var(--border-light)] card-shadow-hover"
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3.5 flex-1 min-w-0">
          <div
            className={`mt-0.5 w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${colors.iconBg} ${colors.icon}`}
          >
            <ModuleIcon icon={info.icon} />
          </div>
          <div className="min-w-0">
            <h3 className="text-[13px] font-semibold text-[var(--text-primary)]">
              {info.label}
            </h3>
            <p className="text-[12px] text-[var(--text-muted)] mt-0.5 leading-relaxed">
              {info.description}
            </p>
          </div>
        </div>
        <button
          onClick={() => onToggle(name)}
          disabled={loading}
          className={`shrink-0 px-3.5 py-1.5 rounded-lg text-[12px] font-medium transition-all duration-150 ${
            active
              ? "bg-red-50 text-red-600 hover:bg-red-100 border border-red-200"
              : "bg-gradient-to-b from-indigo-500 to-indigo-600 text-white hover:from-indigo-600 hover:to-indigo-700 shadow-sm"
          } disabled:opacity-50`}
        >
          {loading ? "..." : active ? "Deaktivieren" : "Aktivieren"}
        </button>
      </div>
      {active && (
        <div className="mt-3 ml-0 sm:ml-[52px] flex items-center gap-1.5">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span className="text-[11px] font-medium text-emerald-600">Aktiv</span>
        </div>
      )}
    </div>
  );
}
