"use client";

import { useEffect, useState } from "react";
import DashboardShell from "@/components/DashboardShell";
import { getCompany, setCompany, CompanyProfile } from "@/lib/api";

const PLATFORM_CONFIG: Record<string, { label: string; icon: string; color: string; bgColor: string }> = {
  google:         { label: "Google Reviews",    icon: "G",  color: "text-blue-600",    bgColor: "bg-blue-50" },
  trustpilot:     { label: "Trustpilot",        icon: "T",  color: "text-emerald-600", bgColor: "bg-emerald-50" },
  kununu:         { label: "Kununu",            icon: "K",  color: "text-teal-600",    bgColor: "bg-teal-50" },
  glassdoor:      { label: "Glassdoor",         icon: "G",  color: "text-green-600",   bgColor: "bg-green-50" },
  provenexpert:   { label: "ProvenExpert",      icon: "P",  color: "text-orange-600",  bgColor: "bg-orange-50" },
  appstore:       { label: "Apple App Store",   icon: "A",  color: "text-sky-600",     bgColor: "bg-sky-50" },
  playstore:      { label: "Google Play Store", icon: "P",  color: "text-indigo-600",  bgColor: "bg-indigo-50" },
  tripadvisor:    { label: "Tripadvisor",       icon: "TA", color: "text-lime-600",    bgColor: "bg-lime-50" },
  jameda:         { label: "Jameda",            icon: "J",  color: "text-cyan-600",    bgColor: "bg-cyan-50" },
  "11880":        { label: "11880.com",         icon: "11", color: "text-yellow-600",  bgColor: "bg-yellow-50" },
  golocal:        { label: "GoLocal",           icon: "GL", color: "text-rose-600",    bgColor: "bg-rose-50" },
  kennstdueinen:  { label: "KennstDuEinen",    icon: "KD", color: "text-violet-600",  bgColor: "bg-violet-50" },
  ekomi:          { label: "eKomi",             icon: "eK", color: "text-amber-600",   bgColor: "bg-amber-50" },
  trustedshops:   { label: "Trusted Shops",    icon: "TS", color: "text-fuchsia-600", bgColor: "bg-fuchsia-50" },
};

const SIZE_OPTIONS = [
  { value: "", label: "Nicht angegeben" },
  { value: "solo", label: "Einzelunternehmen" },
  { value: "klein", label: "Kleinunternehmen (2-20 MA)" },
  { value: "mittel", label: "Mittelstand (20-250 MA)" },
  { value: "gross", label: "Großunternehmen (250+ MA)" },
  { value: "konzern", label: "Konzern / Kette" },
];

const inputClass =
  "w-full px-4 py-3 bg-white border border-[var(--border)] rounded-xl text-[14px] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all";

export default function SettingsPage() {
  const [companyName, setCompanyName] = useState("");
  const [location, setLocation] = useState("");
  const [companySize, setCompanySize] = useState("");

  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    getCompany()
      .then((data) => {
        setCompanyName(data.company_name);
        setLocation(data.location);
        setCompanySize(data.company_size);
        if (data.company_name) setProfile(data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    const name = companyName.trim();
    if (!name) return;

    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const result = await setCompany(name, location.trim(), companySize);
      setProfile(result);
      setSuccess("Firmenprofil gespeichert");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <DashboardShell>
      <div className="mb-8">
        <h1 className="text-xl font-bold text-[var(--text-primary)]">Einstellungen</h1>
        <p className="text-[13px] text-[var(--text-muted)] mt-1">
          Globale Konfiguration deines Unternehmensprofils
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

      {loading ? (
        <div className="space-y-4">
          <div className="h-48 rounded-2xl animate-shimmer" />
          <div className="h-48 rounded-2xl animate-shimmer" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Company Profile Card */}
          <div className="rounded-2xl border border-[var(--border)] bg-white overflow-hidden card-shadow">
            <div className="bg-gradient-to-r from-indigo-500 to-purple-500 px-6 py-4">
              <h2 className="text-white text-[15px] font-bold flex items-center gap-2">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" />
                </svg>
                Unternehmen
              </h2>
            </div>
            <div className="p-6 space-y-5">
              <p className="text-[12px] text-[var(--text-muted)]">
                Diese Daten werden von allen Modulen genutzt. Die Branche und relevanten Plattformen werden automatisch erkannt. Der Standort hilft bei der lokalen Wettbewerber-Erkennung und Google-Suche.
              </p>

              {/* Company Name */}
              <div>
                <label className="text-[12px] font-semibold text-[var(--text-secondary)] mb-1.5 block">
                  Firmenname
                </label>
                <input
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSave()}
                  placeholder="z.B. Pronto Pronto, Stripe, Deutsche Bahn"
                  className={inputClass}
                />
              </div>

              {/* Location + Size row */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-[12px] font-semibold text-[var(--text-secondary)] mb-1.5 block">
                    Standort
                    <span className="font-normal text-[var(--text-muted)] ml-1">(Stadt oder Region)</span>
                  </label>
                  <input
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSave()}
                    placeholder="z.B. Emden, Hamburg, Berlin"
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className="text-[12px] font-semibold text-[var(--text-secondary)] mb-1.5 block">
                    Unternehmensgröße
                  </label>
                  <select
                    value={companySize}
                    onChange={(e) => setCompanySize(e.target.value)}
                    className={inputClass + " appearance-none cursor-pointer"}
                  >
                    {SIZE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Save button */}
              <button
                onClick={handleSave}
                disabled={saving || !companyName.trim()}
                className="px-6 py-3 bg-gradient-to-b from-indigo-500 to-indigo-600 text-white rounded-xl text-[13px] font-semibold hover:from-indigo-600 hover:to-indigo-700 shadow-sm transition-all disabled:opacity-50"
              >
                {saving ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Analysiere...
                  </span>
                ) : (
                  "Speichern & Branche erkennen"
                )}
              </button>
            </div>
          </div>

          {/* Profile Result Card */}
          {profile && (
            <div className="rounded-2xl border border-[var(--border)] bg-white overflow-hidden card-shadow animate-fade-in">
              <div className="p-6">
                {/* Company info header */}
                <div className="flex items-start gap-3 mb-5">
                  <div className="w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center shrink-0">
                    <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-[14px] font-bold text-[var(--text-primary)]">
                      {profile.company_name}
                    </h3>
                    <div className="flex flex-wrap items-center gap-2 mt-1">
                      {profile.industry_label && (
                        <span className="text-[11px] font-semibold text-purple-600 bg-purple-50 px-2 py-0.5 rounded-md">
                          {profile.industry_label}
                        </span>
                      )}
                      {profile.location && (
                        <span className="text-[11px] font-medium text-[var(--text-muted)] flex items-center gap-1">
                          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z" />
                          </svg>
                          {profile.location}
                        </span>
                      )}
                      {profile.company_size_label && (
                        <span className="text-[11px] text-[var(--text-muted)]">
                          {profile.company_size_label}
                        </span>
                      )}
                      {profile.is_local && (
                        <span className="text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md">
                          Lokales Unternehmen
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Platforms */}
                {profile.platforms.length > 0 && (
                  <>
                    <h4 className="text-[11px] font-semibold text-[var(--text-secondary)] mb-3 uppercase tracking-wider">
                      Aktive Review-Plattformen
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                      {profile.platforms.map((p) => {
                        const config = PLATFORM_CONFIG[p];
                        if (!config) return null;
                        return (
                          <div
                            key={p}
                            className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg border border-[var(--border)] bg-[var(--bg-secondary)]"
                          >
                            <div className={`w-7 h-7 rounded-lg ${config.bgColor} ${config.color} flex items-center justify-center text-[11px] font-bold shrink-0`}>
                              {config.icon}
                            </div>
                            <span className="text-[12px] font-medium text-[var(--text-primary)]">
                              {config.label}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                    <p className="text-[11px] text-[var(--text-muted)] mt-3">
                      Basierend auf Branche{profile.is_local ? " und Standort" : ""} werden nur relevante Plattformen abgefragt.
                    </p>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </DashboardShell>
  );
}
