"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import DashboardShell from "@/components/DashboardShell";
import {
  getMe,
  getAdminUsers,
  getAdminStats,
  getPlanConfig,
  updatePlanConfig,
  getAIRouting,
  updateAIRouting,
  AdminUser,
  AdminStats,
  PlanConfigItem,
  AIRoutingTaskInfo,
} from "@/lib/api";

const PLAN_LABELS: Record<string, string> = {
  free: "Free",
  basic: "Basic",
  pro: "Pro",
};

const PROVIDER_OPTIONS: { value: string; label: string }[] = [
  { value: "auto", label: "Automatisch (Gemini, Fallback OpenRouter)" },
  { value: "gemini", label: "Nur Gemini" },
  { value: "openrouter", label: "Nur OpenRouter" },
];

type Tab = "stats" | "einstellungen" | "ki-routing";

export default function AdminPage() {
  return (
    <Suspense fallback={null}>
      <AdminContent />
    </Suspense>
  );
}

function AdminContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialTab = searchParams.get("tab");
  const [tab, setTab] = useState<Tab>(
    initialTab === "einstellungen" ? "einstellungen" : initialTab === "ki-routing" ? "ki-routing" : "stats"
  );

  const [checking, setChecking] = useState(true);
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    getMe()
      .then((me) => {
        if (!me.is_admin) {
          router.replace("/dashboard");
          return;
        }
        setAllowed(true);
      })
      .catch(() => router.replace("/dashboard"))
      .finally(() => setChecking(false));
  }, [router]);

  function switchTab(t: Tab) {
    setTab(t);
    router.replace(`/admin?tab=${t}`, { scroll: false });
  }

  // --- Stats ---
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);

  // --- Einstellungen ---
  const [planConfig, setPlanConfig] = useState<Record<string, PlanConfigItem>>({});
  const [configLoading, setConfigLoading] = useState(true);
  const [savingPlan, setSavingPlan] = useState<string | null>(null);
  const [savedPlan, setSavedPlan] = useState<string | null>(null);

  // --- KI-Routing ---
  const [aiRouting, setAiRouting] = useState<Record<string, AIRoutingTaskInfo>>({});
  const [routingLoading, setRoutingLoading] = useState(true);
  const [savingTask, setSavingTask] = useState<string | null>(null);
  const [savedTask, setSavedTask] = useState<string | null>(null);

  useEffect(() => {
    if (!allowed) return;
    Promise.all([getAdminUsers(), getAdminStats()])
      .then(([u, s]) => {
        setUsers(u);
        setStats(s);
      })
      .catch(() => {})
      .finally(() => setStatsLoading(false));

    getPlanConfig()
      .then(setPlanConfig)
      .catch(() => {})
      .finally(() => setConfigLoading(false));

    getAIRouting()
      .then(setAiRouting)
      .catch(() => {})
      .finally(() => setRoutingLoading(false));
  }, [allowed]);

  function updateField(plan: string, field: keyof PlanConfigItem, value: number | null) {
    setPlanConfig((prev) => ({
      ...prev,
      [plan]: { ...prev[plan], [field]: value },
    }));
  }

  async function handleSavePlan(plan: string) {
    const cfg = planConfig[plan];
    if (!cfg) return;
    setSavingPlan(plan);
    setSavedPlan(null);
    try {
      await updatePlanConfig(plan, cfg);
      setSavedPlan(plan);
      setTimeout(() => setSavedPlan(null), 2000);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSavingPlan(null);
    }
  }

  function updateRoutingField(taskKey: string, provider: string) {
    setAiRouting((prev) => ({
      ...prev,
      [taskKey]: { ...prev[taskKey], provider },
    }));
  }

  async function handleSaveRouting(taskKey: string) {
    const cfg = aiRouting[taskKey];
    if (!cfg) return;
    setSavingTask(taskKey);
    setSavedTask(null);
    try {
      await updateAIRouting(taskKey, cfg.provider);
      setSavedTask(taskKey);
      setTimeout(() => setSavedTask(null), 2000);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSavingTask(null);
    }
  }

  function renderStats() {
    if (statsLoading) {
      return (
        <div className="space-y-4">
          <div className="h-24 rounded-2xl animate-shimmer" />
          <div className="h-96 rounded-2xl animate-shimmer" />
        </div>
      );
    }

    return (
      <div className="space-y-6">
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "User", value: stats.total_users },
              { label: "Aktive Abos", value: stats.active_subscriptions },
              { label: "Reports", value: stats.total_reports },
              { label: "KI-Tokens diesen Monat", value: stats.total_ai_tokens_month.toLocaleString("de-DE") },
            ].map((s) => (
              <div key={s.label} className="rounded-2xl border border-[var(--border)] bg-white p-4 card-shadow">
                <p className="text-[11px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                  {s.label}
                </p>
                <p className="text-[22px] font-bold text-[var(--text-primary)] mt-1">{s.value}</p>
              </div>
            ))}
          </div>
        )}

        <div className="rounded-2xl border border-[var(--border)] bg-white overflow-hidden card-shadow">
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-[var(--border)] bg-[var(--bg-secondary)]">
                  <th className="text-left px-5 py-3 font-semibold text-[var(--text-secondary)]">E-Mail</th>
                  <th className="text-left px-5 py-3 font-semibold text-[var(--text-secondary)]">Plan</th>
                  <th className="text-left px-5 py-3 font-semibold text-[var(--text-secondary)]">Status</th>
                  <th className="text-left px-5 py-3 font-semibold text-[var(--text-secondary)]">Module</th>
                  <th className="text-left px-5 py-3 font-semibold text-[var(--text-secondary)]">KI-Tokens (Monat)</th>
                  <th className="text-left px-5 py-3 font-semibold text-[var(--text-secondary)]">Registriert</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => {
                  const overLimit = u.ai_token_limit !== null && u.ai_tokens_used_month >= u.ai_token_limit;
                  return (
                    <tr key={u.id} className="border-b border-[var(--border)] last:border-0">
                      <td className="px-5 py-3 text-[var(--text-primary)]">
                        {u.email}
                        {u.is_admin && (
                          <span className="ml-2 text-[10px] font-bold text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">
                            ADMIN
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3 text-[var(--text-secondary)] capitalize">{u.plan || "—"}</td>
                      <td className="px-5 py-3 text-[var(--text-secondary)]">{u.status || "—"}</td>
                      <td className="px-5 py-3 text-[var(--text-secondary)]">{u.module_count}</td>
                      <td className={`px-5 py-3 ${overLimit ? "text-red-600 font-bold" : "text-[var(--text-secondary)]"}`}>
                        {u.ai_tokens_used_month.toLocaleString("de-DE")}
                        {u.ai_token_limit !== null && ` / ${u.ai_token_limit.toLocaleString("de-DE")}`}
                      </td>
                      <td className="px-5 py-3 text-[var(--text-muted)]">
                        {new Date(u.created_at).toLocaleDateString("de-DE")}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  function renderEinstellungen() {
    if (configLoading) {
      return (
        <div className="space-y-4">
          <div className="h-40 rounded-2xl animate-shimmer" />
          <div className="h-40 rounded-2xl animate-shimmer" />
          <div className="h-40 rounded-2xl animate-shimmer" />
        </div>
      );
    }

    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {Object.keys(PLAN_LABELS).map((plan) => {
          const cfg = planConfig[plan];
          if (!cfg) return null;
          return (
            <div key={plan} className="rounded-2xl border border-[var(--border)] bg-white p-5 card-shadow space-y-4">
              <h3 className="text-[15px] font-bold text-[var(--text-primary)]">{PLAN_LABELS[plan]}</h3>

              <div>
                <label className="text-[12px] font-semibold text-[var(--text-secondary)] mb-1.5 block">
                  Modul-Limit
                </label>
                <input
                  type="number"
                  min={0}
                  value={cfg.module_limit}
                  onChange={(e) => updateField(plan, "module_limit", Number(e.target.value))}
                  className="w-full px-4 py-2.5 bg-white border border-[var(--border)] rounded-xl text-[14px] text-[var(--text-primary)] focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all"
                />
              </div>

              <div>
                <label className="text-[12px] font-semibold text-[var(--text-secondary)] mb-1.5 block">
                  KI-Token-Limit (Monat)
                  <span className="font-normal text-[var(--text-muted)] ml-1">(leer = kein Limit)</span>
                </label>
                <input
                  type="number"
                  min={0}
                  value={cfg.ai_token_limit ?? ""}
                  onChange={(e) =>
                    updateField(plan, "ai_token_limit", e.target.value === "" ? null : Number(e.target.value))
                  }
                  placeholder="kein Limit"
                  className="w-full px-4 py-2.5 bg-white border border-[var(--border)] rounded-xl text-[14px] text-[var(--text-primary)] focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all"
                />
              </div>

              <button
                onClick={() => handleSavePlan(plan)}
                disabled={savingPlan === plan}
                className="w-full px-4 py-2.5 bg-gradient-to-b from-indigo-500 to-indigo-600 text-white rounded-xl text-[13px] font-semibold hover:from-indigo-600 hover:to-indigo-700 shadow-sm transition-all disabled:opacity-50"
              >
                {savingPlan === plan ? "Speichere..." : savedPlan === plan ? "Gespeichert ✓" : "Speichern"}
              </button>
            </div>
          );
        })}
      </div>
    );
  }

  function renderKiRouting() {
    if (routingLoading) {
      return (
        <div className="space-y-4">
          <div className="h-40 rounded-2xl animate-shimmer" />
          <div className="h-40 rounded-2xl animate-shimmer" />
        </div>
      );
    }

    const grouped: Record<string, [string, AIRoutingTaskInfo][]> = {};
    for (const [taskKey, info] of Object.entries(aiRouting)) {
      if (!grouped[info.module]) grouped[info.module] = [];
      grouped[info.module].push([taskKey, info]);
    }

    return (
      <div className="space-y-6">
        <p className="text-[12px] text-[var(--text-muted)] -mt-2">
          Steuert pro Prompt, welcher KI-Anbieter genutzt wird. &quot;Automatisch&quot; nutzt Gemini und
          weicht bei Fehlern auf OpenRouter aus.
        </p>
        {Object.entries(grouped).map(([module, tasks]) => (
          <div key={module} className="rounded-2xl border border-[var(--border)] bg-white overflow-hidden card-shadow">
            <div className="px-5 py-3 border-b border-[var(--border)] bg-[var(--bg-secondary)]">
              <h3 className="text-[13px] font-bold text-[var(--text-primary)]">{module}</h3>
            </div>
            <div className="divide-y divide-[var(--border)]">
              {tasks.map(([taskKey, info]) => (
                <div key={taskKey} className="flex flex-col sm:flex-row sm:items-center gap-3 px-5 py-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-medium text-[var(--text-primary)]">{info.label}</p>
                  </div>
                  <select
                    value={aiRouting[taskKey]?.provider ?? "auto"}
                    onChange={(e) => updateRoutingField(taskKey, e.target.value)}
                    className="px-3 py-2 bg-white border border-[var(--border)] rounded-lg text-[13px] text-[var(--text-primary)] focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all sm:w-[300px]"
                  >
                    {PROVIDER_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => handleSaveRouting(taskKey)}
                    disabled={savingTask === taskKey}
                    className="px-4 py-2 bg-gradient-to-b from-indigo-500 to-indigo-600 text-white rounded-lg text-[12px] font-semibold hover:from-indigo-600 hover:to-indigo-700 shadow-sm transition-all disabled:opacity-50 shrink-0"
                  >
                    {savingTask === taskKey ? "..." : savedTask === taskKey ? "Gespeichert ✓" : "Speichern"}
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (checking || !allowed) {
    return (
      <DashboardShell>
        <div className="h-96 rounded-2xl animate-shimmer" />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell>
      <div className="mb-6">
        <h1 className="text-xl font-bold text-[var(--text-primary)]">Admin</h1>
        <p className="text-[13px] text-[var(--text-muted)] mt-1">
          Plattform-Statistiken und Abo-Parameter verwalten
        </p>
      </div>

      <div className="flex gap-1 mb-6 border-b border-[var(--border)]">
        <button
          onClick={() => switchTab("stats")}
          className={`px-4 py-2.5 text-[13px] font-semibold border-b-2 -mb-px transition-colors ${
            tab === "stats"
              ? "border-indigo-500 text-indigo-600"
              : "border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
          }`}
        >
          Stats
        </button>
        <button
          onClick={() => switchTab("einstellungen")}
          className={`px-4 py-2.5 text-[13px] font-semibold border-b-2 -mb-px transition-colors ${
            tab === "einstellungen"
              ? "border-indigo-500 text-indigo-600"
              : "border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
          }`}
        >
          Einstellungen
        </button>
        <button
          onClick={() => switchTab("ki-routing")}
          className={`px-4 py-2.5 text-[13px] font-semibold border-b-2 -mb-px transition-colors ${
            tab === "ki-routing"
              ? "border-indigo-500 text-indigo-600"
              : "border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
          }`}
        >
          KI-Routing
        </button>
      </div>

      {tab === "stats" && renderStats()}
      {tab === "einstellungen" && renderEinstellungen()}
      {tab === "ki-routing" && renderKiRouting()}
    </DashboardShell>
  );
}
