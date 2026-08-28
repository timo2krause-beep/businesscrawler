"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import DashboardShell from "@/components/DashboardShell";
import ModuleCard from "@/components/ModuleCard";
import {
  getMe,
  getModules,
  subscribeModule,
  unsubscribeModule,
  runModule,
  getPreferences,
  setPreference,
  refreshCompetitors,
  getCompetitors,
  addCompetitor,
  toggleCompetitor,
  deleteCompetitor,
  Competitor,
} from "@/lib/api";
import { MODULE_INFO, VISIBLE_MODULES, getModulesByCategory } from "@/lib/modules";

interface ModuleInfo {
  name: string;
  description: string;
}

interface ScrapingTarget {
  url: string;
  name: string;
  selector: string;
}

const inputClass =
  "w-full px-3 py-2 bg-white border border-[var(--border)] rounded-lg text-[13px] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all";
const btnPrimary =
  "px-4 py-2 bg-gradient-to-b from-indigo-500 to-indigo-600 text-white rounded-lg text-[12px] font-semibold hover:from-indigo-600 hover:to-indigo-700 shadow-sm transition-all disabled:opacity-50";
const btnSecondary =
  "px-4 py-2 bg-white border border-[var(--border)] text-[var(--text-secondary)] rounded-lg text-[12px] font-medium hover:bg-[var(--bg-secondary)] hover:border-[var(--border-light)] transition-all disabled:opacity-50";

export default function ModulesPage() {
  const router = useRouter();
  const [allModules, setAllModules] = useState<ModuleInfo[]>([]);
  const [userModules, setUserModules] = useState<string[]>([]);
  const [, setPlan] = useState("free");
  const [loading, setLoading] = useState<string | null>(null);
  const [running, setRunning] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Expanded settings panel per module
  const [expanded, setExpanded] = useState<string | null>(null);

  // Preferences
  const [targets, setTargets] = useState<ScrapingTarget[]>([]);
  const [targetInput, setTargetInput] = useState({ url: "", name: "", selector: "main" });
  const [savingPref, setSavingPref] = useState<string | null>(null);

  // Competitors (for ki_wettbewerb)
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [competitorInput, setCompetitorInput] = useState({ name: "", url: "" });
  const [refreshing, setRefreshing] = useState(false);
  const [addingCompetitor, setAddingCompetitor] = useState(false);

  // Generic string-list preferences (watched_repos, cve_keywords)
  const [listPrefs, setListPrefs] = useState<Record<string, string[]>>({});
  const [listInput, setListInput] = useState<Record<string, string>>({});

  // RSS Feeds (url + name)
  const [feeds, setFeeds] = useState<{ url: string; name: string }[]>([]);
  const [feedInput, setFeedInput] = useState({ url: "", name: "" });

  useEffect(() => {
    async function load() {
      const [mods, me, userPrefs] = await Promise.all([
        getModules(),
        getMe(),
        getPreferences().catch(() => []),
      ]);
      setAllModules(mods.modules);
      setUserModules(me.modules);
      setPlan(me.plan);

      for (const p of userPrefs as any[]) {
        if (p.key === "scraping_targets") {
          setTargets(Array.isArray(p.value) ? p.value : []);
        } else if (p.key === "rss_feeds") {
          setFeeds(Array.isArray(p.value) ? p.value : []);
        } else if (Array.isArray(p.value)) {
          setListPrefs((prev) => ({ ...prev, [p.key]: p.value }));
        }
      }

      // Load competitors
      getCompetitors().then(setCompetitors).catch(() => {});
    }
    load();
  }, []);

  const visibleModules = allModules.filter((m) => VISIBLE_MODULES.includes(m.name));
  const marketingModules = visibleModules.filter((m) => getModulesByCategory("marketing").includes(m.name));
  const techModules = visibleModules.filter((m) => getModulesByCategory("tech").includes(m.name));

  async function handleToggle(name: string) {
    setError("");
    setSuccess("");
    setLoading(name);
    try {
      if (userModules.includes(name)) {
        await unsubscribeModule(name);
        setUserModules((prev) => prev.filter((m) => m !== name));
        setExpanded(null);
      } else {
        await subscribeModule(name);
        setUserModules((prev) => [...prev, name]);
        setExpanded(name);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(null);
    }
  }

  async function handleRun(name: string) {
    setError("");
    setRunning(name);
    try {
      const result = await runModule(name);
      if (result.report_id) {
        router.push(`/reports?id=${result.report_id}`);
      } else {
        setSuccess(`Report generiert: ${result.item_count} Items`);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setRunning(null);
    }
  }

  // --- Targets (Wettbewerbs-Monitor) ---

  function handleAddTarget() {
    const url = targetInput.url.trim();
    if (!url) return;
    if (targets.some((t) => t.url === url)) return;
    setTargets([...targets, { url, name: targetInput.name.trim() || url, selector: targetInput.selector.trim() || "main" }]);
    setTargetInput({ url: "", name: "", selector: "main" });
  }

  async function handleSaveTargets() {
    setSavingPref("scraping_targets");
    setError("");
    try {
      await setPreference("scraping_targets", targets);
      setSuccess("Webseiten gespeichert");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSavingPref(null);
    }
  }

  // --- Generic string lists (watched_repos, cve_keywords) ---

  function handleAddListItem(key: string) {
    const value = (listInput[key] || "").trim();
    if (!value) return;
    setListPrefs((prev) => {
      const current = prev[key] || [];
      if (current.includes(value)) return prev;
      return { ...prev, [key]: [...current, value] };
    });
    setListInput((prev) => ({ ...prev, [key]: "" }));
  }

  function handleRemoveListItem(key: string, value: string) {
    setListPrefs((prev) => ({ ...prev, [key]: (prev[key] || []).filter((v) => v !== value) }));
  }

  async function handleSaveList(key: string) {
    setSavingPref(key);
    setError("");
    try {
      await setPreference(key, listPrefs[key] || []);
      setSuccess("Gespeichert");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSavingPref(null);
    }
  }

  // --- RSS Feeds (rss_monitor) ---

  function handleAddFeed() {
    const url = feedInput.url.trim();
    if (!url) return;
    if (feeds.some((f) => f.url === url)) return;
    setFeeds([...feeds, { url, name: feedInput.name.trim() || url }]);
    setFeedInput({ url: "", name: "" });
  }

  function handleRemoveFeed(url: string) {
    setFeeds(feeds.filter((f) => f.url !== url));
  }

  async function handleSaveFeeds() {
    setSavingPref("rss_feeds");
    setError("");
    try {
      await setPreference("rss_feeds", feeds);
      setSuccess("RSS-Feeds gespeichert");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSavingPref(null);
    }
  }

  // --- Competitors ---

  async function handleAddCompetitor() {
    const name = competitorInput.name.trim();
    if (!name) return;
    setAddingCompetitor(true);
    setError("");
    try {
      const comp = await addCompetitor(name, competitorInput.url);
      setCompetitors((prev) => [...prev, comp]);
      setCompetitorInput({ name: "", url: "" });
      setSuccess(`${name} hinzugefügt`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setAddingCompetitor(false);
    }
  }

  async function handleToggleCompetitor(id: number, active: boolean) {
    try {
      await toggleCompetitor(id, active);
      setCompetitors((prev) => prev.map((c) => (c.id === id ? { ...c, is_active: active } : c)));
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function handleDeleteCompetitor(id: number) {
    try {
      await deleteCompetitor(id);
      setCompetitors((prev) => prev.filter((c) => c.id !== id));
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function handleRefreshCompetitors() {
    setRefreshing(true);
    setError("");
    try {
      const result = await refreshCompetitors();
      setSuccess(result.detail);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setRefreshing(false);
    }
  }

  function toggleExpanded(name: string) {
    setExpanded(expanded === name ? null : name);
  }

  // --- Settings panels per module ---

  function renderSettings(modName: string) {
    const info = MODULE_INFO[modName];
    if (!info) return null;

    // Competitors editor for ki_wettbewerb
    if (info.pref_type === "competitors") {
      const aiCompetitors = competitors.filter((c) => !c.is_custom);
      const customCompetitors = competitors.filter((c) => c.is_custom);

      return (
        <div className="space-y-4">
          {/* AI-detected competitors */}
          {aiCompetitors.length > 0 && (
            <div>
              <h4 className="text-[11px] font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">
                KI-erkannte Wettbewerber
              </h4>
              <div className="space-y-1.5">
                {aiCompetitors.map((c) => (
                  <div
                    key={c.id}
                    className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg border transition-all ${
                      c.is_active
                        ? "bg-white border-[var(--border)] card-shadow"
                        : "bg-[var(--bg-secondary)] border-[var(--border)] opacity-60"
                    }`}
                  >
                    <button
                      onClick={() => handleToggleCompetitor(c.id, !c.is_active)}
                      className={`w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
                        c.is_active
                          ? "bg-indigo-500 border-indigo-500"
                          : "bg-white border-[var(--border-light)]"
                      }`}
                    >
                      {c.is_active && (
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                        </svg>
                      )}
                    </button>
                    <div className="flex-1 min-w-0">
                      <span className={`text-[12px] font-medium ${c.is_active ? "text-[var(--text-primary)]" : "text-[var(--text-muted)] line-through"}`}>
                        {c.name}
                      </span>
                      <span className="text-[11px] text-[var(--text-muted)] ml-2">
                        {c.reason}
                      </span>
                    </div>
                    {c.url && (
                      <a href={c.url} target="_blank" rel="noopener noreferrer" className="text-[11px] text-indigo-500 hover:underline shrink-0">
                        {new URL(c.url).hostname}
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {aiCompetitors.length === 0 && (
            <p className="text-[12px] text-[var(--text-muted)] italic">
              Noch keine KI-Wettbewerber erkannt. Generiere einen Report, um Wettbewerber zu identifizieren.
            </p>
          )}

          {/* Custom competitors */}
          <div>
            <h4 className="text-[11px] font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">
              Eigene Wettbewerber
            </h4>
            {customCompetitors.length > 0 && (
              <div className="space-y-1.5 mb-3">
                {customCompetitors.map((c) => (
                  <div
                    key={c.id}
                    className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg border border-[var(--border)] bg-white card-shadow"
                  >
                    <button
                      onClick={() => handleToggleCompetitor(c.id, !c.is_active)}
                      className={`w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
                        c.is_active
                          ? "bg-indigo-500 border-indigo-500"
                          : "bg-white border-[var(--border-light)]"
                      }`}
                    >
                      {c.is_active && (
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                        </svg>
                      )}
                    </button>
                    <span className={`text-[12px] font-medium flex-1 ${c.is_active ? "text-[var(--text-primary)]" : "text-[var(--text-muted)] line-through"}`}>
                      {c.name}
                    </span>
                    <button
                      onClick={() => handleDeleteCompetitor(c.id)}
                      className="text-[var(--text-muted)] hover:text-red-500 transition-colors text-sm shrink-0"
                    >
                      &times;
                    </button>
                  </div>
                ))}
              </div>
            )}
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="text"
                value={competitorInput.name}
                onChange={(e) => setCompetitorInput({ ...competitorInput, name: e.target.value })}
                onKeyDown={(e) => e.key === "Enter" && handleAddCompetitor()}
                placeholder="Firmenname (z.B. Hubspot)"
                className={inputClass}
              />
              <input
                type="text"
                value={competitorInput.url}
                onChange={(e) => setCompetitorInput({ ...competitorInput, url: e.target.value })}
                onKeyDown={(e) => e.key === "Enter" && handleAddCompetitor()}
                placeholder="URL (optional)"
                className={inputClass + " sm:max-w-[200px]"}
              />
              <button onClick={handleAddCompetitor} disabled={addingCompetitor} className={btnSecondary + " sm:shrink-0"}>
                {addingCompetitor ? "..." : "+"}
              </button>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-2 border-t border-[var(--border)]">
            <button onClick={handleRefreshCompetitors} disabled={refreshing} className={btnSecondary}>
              {refreshing ? "..." : "KI-Analyse neu starten"}
            </button>
          </div>
        </div>
      );
    }

    // Target editor for wettbewerbs_monitor
    if (info.pref_type === "targets") {
      return (
        <div className="space-y-3">
          {targets.length > 0 && (
            <div className="space-y-1.5">
              {targets.map((t) => (
                <div key={t.url} className="flex items-center justify-between gap-3 px-3.5 py-2.5 rounded-lg bg-white border border-[var(--border)] card-shadow">
                  <div className="min-w-0 flex-1">
                    <p className="text-[12px] font-medium text-[var(--text-primary)] truncate">{t.name}</p>
                    <p className="text-[11px] text-[var(--text-muted)] truncate">
                      {t.url}
                      <span className="ml-2 opacity-60">Selector: {t.selector}</span>
                    </p>
                  </div>
                  <button
                    onClick={() => setTargets(targets.filter((x) => x.url !== t.url))}
                    className="text-[var(--text-muted)] hover:text-red-500 transition-colors text-sm shrink-0"
                  >
                    &times;
                  </button>
                </div>
              ))}
            </div>
          )}
          <div className="space-y-2">
            <input type="text" value={targetInput.url} onChange={(e) => setTargetInput({ ...targetInput, url: e.target.value })} placeholder="URL (z.B. https://competitor.com/pricing)" className={inputClass} />
            <div className="flex flex-col sm:flex-row gap-2">
              <input type="text" value={targetInput.name} onChange={(e) => setTargetInput({ ...targetInput, name: e.target.value })} placeholder="Name" className={inputClass} />
              <input type="text" value={targetInput.selector} onChange={(e) => setTargetInput({ ...targetInput, selector: e.target.value })} placeholder="CSS Selector (main)" className={inputClass} />
            </div>
            <button onClick={handleAddTarget} className={btnSecondary}>+ Webseite hinzufügen</button>
          </div>
          <button onClick={handleSaveTargets} disabled={savingPref === "scraping_targets"} className={btnPrimary}>
            {savingPref === "scraping_targets" ? "..." : "Speichern"}
          </button>
        </div>
      );
    }

    // Company-based modules: hint to settings
    if (info.pref_type === "company") {
      return (
        <div className="flex items-center gap-3">
          <svg className="w-4 h-4 text-indigo-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
          </svg>
          <p className="text-[12px] text-[var(--text-secondary)]">
            Nutzt den globalen Firmennamen aus{" "}
            <a href="/account" className="text-indigo-600 font-semibold hover:underline">Account</a>.
          </p>
        </div>
      );
    }

    // RSS-Feed-Editor (rss_monitor): braucht URL + Name statt nur einem String
    if (info.pref_key === "rss_feeds") {
      return (
        <div className="space-y-3">
          {feeds.length > 0 && (
            <div className="space-y-1.5">
              {feeds.map((f) => (
                <div key={f.url} className="flex items-center justify-between gap-3 px-3.5 py-2.5 rounded-lg bg-white border border-[var(--border)] card-shadow">
                  <div className="min-w-0 flex-1">
                    <p className="text-[12px] font-medium text-[var(--text-primary)] truncate">{f.name}</p>
                    <p className="text-[11px] text-[var(--text-muted)] truncate">{f.url}</p>
                  </div>
                  <button
                    onClick={() => handleRemoveFeed(f.url)}
                    className="text-[var(--text-muted)] hover:text-red-500 transition-colors text-sm shrink-0"
                  >
                    &times;
                  </button>
                </div>
              ))}
            </div>
          )}
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              type="text"
              value={feedInput.url}
              onChange={(e) => setFeedInput({ ...feedInput, url: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && handleAddFeed()}
              placeholder={info.pref_placeholder}
              className={inputClass}
            />
            <input
              type="text"
              value={feedInput.name}
              onChange={(e) => setFeedInput({ ...feedInput, name: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && handleAddFeed()}
              placeholder="Name"
              className={inputClass + " sm:max-w-[160px]"}
            />
            <button onClick={handleAddFeed} className={btnSecondary + " sm:shrink-0"}>+</button>
          </div>
          <button onClick={handleSaveFeeds} disabled={savingPref === "rss_feeds"} className={btnPrimary}>
            {savingPref === "rss_feeds" ? "..." : "Speichern"}
          </button>
        </div>
      );
    }

    // Generischer String-Listen-Editor (watched_repos, cve_keywords)
    if (!info.pref_type && info.pref_key) {
      const key = info.pref_key;
      const items = listPrefs[key] || [];
      return (
        <div className="space-y-3">
          {items.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {items.map((item) => (
                <span
                  key={item}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-[var(--border)] text-[12px] font-medium text-[var(--text-primary)] card-shadow"
                >
                  {item}
                  <button
                    onClick={() => handleRemoveListItem(key, item)}
                    className="text-[var(--text-muted)] hover:text-red-500 transition-colors"
                  >
                    &times;
                  </button>
                </span>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <input
              type="text"
              value={listInput[key] || ""}
              onChange={(e) => setListInput((prev) => ({ ...prev, [key]: e.target.value }))}
              onKeyDown={(e) => e.key === "Enter" && handleAddListItem(key)}
              placeholder={info.pref_placeholder}
              className={inputClass}
            />
            <button onClick={() => handleAddListItem(key)} className={btnSecondary + " shrink-0"}>+</button>
          </div>
          <button onClick={() => handleSaveList(key)} disabled={savingPref === key} className={btnPrimary}>
            {savingPref === key ? "..." : "Speichern"}
          </button>
        </div>
      );
    }

    return null;
  }

  function renderModuleList(mods: ModuleInfo[]) {
    return (
      <div className="space-y-3">
        {mods.map((mod) => {
          const active = userModules.includes(mod.name);
          const isExpanded = expanded === mod.name;
          const settings = renderSettings(mod.name);

          return (
            <div key={mod.name}>
              <ModuleCard
                name={mod.name}
                active={active}
                loading={loading === mod.name}
                onToggle={handleToggle}
              />

              {active && (
                <div className="mt-2 ml-0 sm:ml-[52px] space-y-3">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleRun(mod.name)}
                      disabled={running === mod.name}
                      className={btnSecondary}
                    >
                      {running === mod.name ? (
                        <span className="flex items-center gap-2">
                          <svg className="animate-spin w-3 h-3" viewBox="0 0 24 24" fill="none">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                          </svg>
                          Wird generiert...
                        </span>
                      ) : (
                        "Report generieren"
                      )}
                    </button>

                    {settings && (
                      <button
                        onClick={() => toggleExpanded(mod.name)}
                        className={`px-3 py-2 rounded-lg text-[12px] font-medium transition-all ${
                          isExpanded
                            ? "bg-indigo-50 text-indigo-600 border border-indigo-200"
                            : "bg-white border border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)]"
                        }`}
                      >
                        <span className="flex items-center gap-1.5">
                          <svg className={`w-3.5 h-3.5 transition-transform ${isExpanded ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                          </svg>
                          Einstellungen
                        </span>
                      </button>
                    )}
                  </div>

                  {/* Collapsible settings */}
                  {isExpanded && settings && (
                    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-secondary)] p-5 animate-fade-in">
                      {settings}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <DashboardShell>
      <div className="mb-8">
        <h1 className="text-xl font-bold text-[var(--text-primary)]">Module</h1>
        <p className="text-[13px] text-[var(--text-muted)] mt-1">
          Marketing-Module zur Wettbewerbs- und Reputationsanalyse
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-[12px] px-4 py-3 rounded-xl mb-4">
          <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
          </svg>
          {error}
        </div>
      )}
      {success && (
        <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 text-emerald-700 text-[12px] px-4 py-3 rounded-xl mb-4">
          <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
          </svg>
          {success}
        </div>
      )}

      {renderModuleList(marketingModules)}

      {techModules.length > 0 && (
        <div className="mt-12">
          <div className="mb-4 pt-6 border-t border-[var(--border)]">
            <h2 className="text-[15px] font-bold text-[var(--text-primary)]">Tech-Module</h2>
            <p className="text-[12px] text-[var(--text-muted)] mt-1">
              Zusätzliche Monitore für Entwicklungsteams: Releases, Sicherheitslücken und News-Feeds
            </p>
          </div>
          {renderModuleList(techModules)}
        </div>
      )}
    </DashboardShell>
  );
}
