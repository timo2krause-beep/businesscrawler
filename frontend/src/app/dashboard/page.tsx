"use client";

import { useEffect, useState } from "react";
import DashboardShell from "@/components/DashboardShell";
import ReportCard from "@/components/ReportCard";
import { getMe, getReports } from "@/lib/api";
import { getModuleLabel, MODULE_INFO } from "@/lib/modules";

interface User {
  id: number;
  email: string;
  plan: string;
  modules: string[];
}

interface Report {
  id: number;
  module: string;
  content_md: string;
  created_at: string;
}

const STAT_CONFIGS = [
  {
    key: "plan",
    label: "Plan",
    gradient: "from-indigo-500 to-purple-500",
    iconBg: "bg-indigo-50",
    iconColor: "text-indigo-600",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
      </svg>
    ),
  },
  {
    key: "modules",
    label: "Aktive Module",
    gradient: "from-emerald-500 to-teal-500",
    iconBg: "bg-emerald-50",
    iconColor: "text-emerald-600",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6Z" />
      </svg>
    ),
  },
  {
    key: "reports",
    label: "Reports",
    gradient: "from-orange-500 to-amber-500",
    iconBg: "bg-orange-50",
    iconColor: "text-orange-600",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
      </svg>
    ),
  },
];

const MODULE_BADGE_COLORS: Record<string, string> = {
  blue:    "text-blue-700 bg-blue-50 border-blue-100",
  purple:  "text-purple-700 bg-purple-50 border-purple-100",
  orange:  "text-orange-700 bg-orange-50 border-orange-100",
  emerald: "text-emerald-700 bg-emerald-50 border-emerald-100",
  pink:    "text-pink-700 bg-pink-50 border-pink-100",
  cyan:    "text-cyan-700 bg-cyan-50 border-cyan-100",
  amber:   "text-amber-700 bg-amber-50 border-amber-100",
};

export default function DashboardPage() {
  const [user, setUser] = useState<User | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [u, r] = await Promise.all([getMe(), getReports()]);
        setUser(u);
        setReports(r);
      } catch {
        // Auth redirect handled by API client
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <DashboardShell>
        <div className="space-y-4">
          <div className="h-8 w-48 rounded-lg animate-shimmer" />
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 rounded-xl animate-shimmer" />
            ))}
          </div>
        </div>
      </DashboardShell>
    );
  }

  const statValues = {
    plan: (user?.plan || "Free").charAt(0).toUpperCase() + (user?.plan || "free").slice(1),
    modules: String(user?.modules.length || 0),
    reports: String(reports.length),
  };

  return (
    <DashboardShell>
      <div className="mb-8">
        <h1 className="text-xl font-bold text-[var(--text-primary)]">
          Willkommen zurück
        </h1>
        <p className="text-[13px] text-[var(--text-muted)] mt-1">
          Hier ist dein aktueller Überblick.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {STAT_CONFIGS.map((stat) => (
          <div
            key={stat.key}
            className="rounded-xl border border-[var(--border)] bg-white p-5 card-shadow"
          >
            <div className="flex items-center justify-between">
              <p className="text-[11px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                {stat.label}
              </p>
              <div className={`w-9 h-9 rounded-lg ${stat.iconBg} ${stat.iconColor} flex items-center justify-center`}>
                {stat.icon}
              </div>
            </div>
            <p className="text-2xl font-bold text-[var(--text-primary)] mt-2">
              {statValues[stat.key as keyof typeof statValues]}
            </p>
          </div>
        ))}
      </div>

      {/* Active Modules */}
      {user && user.modules.length > 0 && (
        <div className="mb-8">
          <h2 className="text-[13px] font-semibold text-[var(--text-primary)] mb-3">
            Aktive Module
          </h2>
          <div className="flex flex-wrap gap-2">
            {user.modules.map((m) => {
              const info = MODULE_INFO[m];
              const badgeColor = MODULE_BADGE_COLORS[info?.color || "blue"] || MODULE_BADGE_COLORS.blue;
              return (
                <span
                  key={m}
                  className={`px-3 py-1.5 rounded-lg text-[11px] font-semibold border ${badgeColor}`}
                >
                  {getModuleLabel(m)}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Recent Reports */}
      <div>
        <h2 className="text-[13px] font-semibold text-[var(--text-primary)] mb-3">
          Letzte Reports
        </h2>
        {reports.length === 0 ? (
          <div className="rounded-xl border border-dashed border-[var(--border)] bg-[var(--bg-secondary)] p-8 text-center">
            <div className="w-12 h-12 rounded-xl bg-indigo-50 flex items-center justify-center mx-auto mb-3">
              <svg className="w-6 h-6 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
              </svg>
            </div>
            <p className="text-[13px] font-medium text-[var(--text-primary)]">
              Noch keine Reports
            </p>
            <p className="text-[12px] text-[var(--text-muted)] mt-1">
              Aktiviere ein Modul und generiere deinen ersten Report.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {reports.slice(0, 5).map((r) => (
              <ReportCard
                key={r.id}
                id={r.id}
                module={r.module}
                created_at={r.created_at}
                preview={r.content_md.slice(0, 120)}
              />
            ))}
          </div>
        )}
      </div>
    </DashboardShell>
  );
}
