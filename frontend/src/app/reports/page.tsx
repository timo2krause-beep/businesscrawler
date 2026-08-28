"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import DashboardShell from "@/components/DashboardShell";
import ReportCard from "@/components/ReportCard";
import { getReports, getReport } from "@/lib/api";
import { getModuleLabel } from "@/lib/modules";
import { stripMarkdownPreview } from "@/lib/text";

interface Report {
  id: number;
  module: string;
  content_md: string;
  created_at: string;
}

interface ReportDetail {
  id: number;
  module: string;
  content_md: string;
  content_html: string;
  raw_data: Record<string, unknown> | null;
  created_at: string;
}

interface PlatformData {
  platform: string;
  avg_rating: number | null;
  review_count: number | string | null;
}

/* ── Platform config ── */

const PLATFORM_CONFIG: Record<
  string,
  { label: string; color: string; bgColor: string; icon: string }
> = {
  google:       { label: "Google",       color: "text-blue-600",    bgColor: "bg-blue-50",    icon: "G" },
  trustpilot:   { label: "Trustpilot",   color: "text-emerald-600", bgColor: "bg-emerald-50", icon: "T" },
  kununu:       { label: "Kununu",       color: "text-teal-600",    bgColor: "bg-teal-50",    icon: "K" },
  glassdoor:    { label: "Glassdoor",    color: "text-green-600",   bgColor: "bg-green-50",   icon: "G" },
  provenexpert: { label: "ProvenExpert", color: "text-orange-600",  bgColor: "bg-orange-50",  icon: "P" },
  appstore:     { label: "App Store",    color: "text-sky-600",     bgColor: "bg-sky-50",     icon: "A" },
  playstore:    { label: "Play Store",   color: "text-indigo-600",  bgColor: "bg-indigo-50",  icon: "P" },
};

/* ── Stars ── */

function StarRating({ rating }: { rating: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-0.5">
        {Array.from({ length: 5 }).map((_, i) => {
          const fill = Math.min(Math.max(rating - i, 0), 1);
          return (
            <div key={i} className="relative w-4 h-4">
              <svg className="w-4 h-4 text-slate-200" fill="currentColor" viewBox="0 0 24 24">
                <path d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z" />
              </svg>
              {fill > 0 && (
                <div
                  className="absolute inset-0 overflow-hidden"
                  style={{ width: `${fill * 100}%` }}
                >
                  <svg className="w-4 h-4 text-amber-400" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z" />
                  </svg>
                </div>
              )}
            </div>
          );
        })}
      </div>
      <span className="text-[14px] font-bold text-[var(--text-primary)]">
        {rating.toFixed(1)}
      </span>
    </div>
  );
}

/* ── Rating bar ── */

function RatingBar({ rating }: { rating: number }) {
  const pct = Math.min((rating / 5) * 100, 100);
  let barColor = "bg-red-400";
  if (rating >= 4) barColor = "bg-emerald-500";
  else if (rating >= 3) barColor = "bg-amber-400";
  else if (rating >= 2) barColor = "bg-orange-400";

  return (
    <div className="w-full bg-slate-100 rounded-full h-2 mt-2">
      <div
        className={`h-2 rounded-full ${barColor} transition-all duration-500`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

/* ── Single platform card ── */

function PlatformCard({ data }: { data: PlatformData }) {
  const config = PLATFORM_CONFIG[data.platform] || {
    label: data.platform,
    color: "text-slate-600",
    bgColor: "bg-slate-50",
    icon: "?",
  };

  const rating = data.avg_rating != null ? Number(data.avg_rating) : null;
  const count = data.review_count;

  return (
    <div className="rounded-xl border border-[var(--border)] bg-white p-4 card-shadow">
      <div className="flex items-center gap-2.5 mb-3">
        <div
          className={`w-8 h-8 rounded-lg ${config.bgColor} ${config.color} flex items-center justify-center text-[13px] font-bold shrink-0`}
        >
          {config.icon}
        </div>
        <div className="min-w-0">
          <p className="text-[13px] font-semibold text-[var(--text-primary)]">
            {config.label}
          </p>
          {count != null && (
            <p className="text-[11px] text-[var(--text-muted)]">
              {count} Bewertungen
            </p>
          )}
        </div>
      </div>
      {rating != null && rating <= 5 ? (
        <>
          <StarRating rating={rating} />
          <RatingBar rating={rating} />
        </>
      ) : rating != null ? (
        <p className="text-[14px] font-bold text-[var(--text-primary)]">
          {rating}/10
        </p>
      ) : (
        <p className="text-[12px] text-[var(--text-muted)] italic">
          Keine Bewertung
        </p>
      )}
    </div>
  );
}

/* ── Hard Facts overview ── */

function HardFacts({ rawData }: { rawData: Record<string, unknown> | null }) {
  if (!rawData) return null;

  const platforms = (rawData.platforms as PlatformData[]) || [];
  if (platforms.length === 0) return null;

  // Only average ratings that are on a /5 scale
  const validRatings = platforms.filter(
    (p) => p.avg_rating != null && Number(p.avg_rating) <= 5
  );
  const avgOverall =
    validRatings.length > 0
      ? validRatings.reduce((sum, p) => sum + Number(p.avg_rating || 0), 0) /
        validRatings.length
      : null;

  const totalReviews = platforms.reduce((sum, p) => {
    const c =
      typeof p.review_count === "string"
        ? parseInt(p.review_count.replace(/[.,]/g, ""), 10)
        : p.review_count;
    return sum + (c || 0);
  }, 0);

  return (
    <div className="mb-6">
      <h2 className="text-[14px] font-bold text-[var(--text-primary)] mb-4 flex items-center gap-2">
        <svg
          className="w-4 h-4 text-indigo-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z"
          />
        </svg>
        Plattform-Übersicht
      </h2>

      {/* Summary row */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 p-5 text-white card-shadow">
          <p className="text-[11px] font-semibold opacity-80 uppercase tracking-wider">
            Durchschnitt
          </p>
          <p className="text-3xl font-extrabold mt-1.5">
            {avgOverall != null ? avgOverall.toFixed(1) : "–"}
            <span className="text-[14px] font-semibold opacity-60">/5</span>
          </p>
        </div>
        <div className="rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 p-5 text-white card-shadow">
          <p className="text-[11px] font-semibold opacity-80 uppercase tracking-wider">
            Bewertungen gesamt
          </p>
          <p className="text-3xl font-extrabold mt-1.5">
            {totalReviews.toLocaleString("de-DE")}
          </p>
        </div>
      </div>

      {/* Platform cards grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {platforms.map((p) => (
          <PlatformCard key={p.platform} data={p} />
        ))}
      </div>
    </div>
  );
}

/* ── Report title for header ── */

const MODULE_TITLES: Record<string, string> = {
  review_monitor: "Bewertungs-Analyse",
  social_sentiment: "Sentiment-Analyse",
  ki_wettbewerb: "KI-Wettbewerbsanalyse",
  wettbewerbs_monitor: "Wettbewerbs-Report",
  tech_stack_monitor: "Tech-Stack Report",
  cve_monitor: "Security Report",
  rss_monitor: "News Report",
};

/* ── Page ── */

function ReportsContent() {
  const searchParams = useSearchParams();
  const selectedId = searchParams.get("id");

  const [reports, setReports] = useState<Report[]>([]);
  const [detail, setDetail] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    getReports().then(setReports).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selectedId) {
      setDetail(null);
      setDetailLoading(true);
      getReport(Number(selectedId))
        .then(setDetail)
        .finally(() => setDetailLoading(false));
    } else {
      setDetail(null);
    }
  }, [selectedId]);

  function handleBack() {
    setDetail(null);
    window.history.pushState({}, "", "/reports");
  }

  return (
    <DashboardShell>
      {/* Page header — only on list view */}
      {!detail && !detailLoading && (
        <div className="mb-8">
          <h1 className="text-xl font-bold text-[var(--text-primary)]">
            Reports
          </h1>
          <p className="text-[13px] text-[var(--text-muted)] mt-1">
            {reports.length} Reports vorhanden
          </p>
        </div>
      )}

      {/* Loading states */}
      {(loading || detailLoading) && (
        <div className="space-y-3">
          {detailLoading && (
            <>
              <div className="h-24 rounded-2xl animate-shimmer" />
              <div className="grid grid-cols-2 gap-3">
                <div className="h-28 rounded-xl animate-shimmer" />
                <div className="h-28 rounded-xl animate-shimmer" />
              </div>
              <div className="grid grid-cols-3 gap-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-32 rounded-xl animate-shimmer" />
                ))}
              </div>
              <div className="h-64 rounded-2xl animate-shimmer" />
            </>
          )}
          {loading &&
            !detailLoading &&
            [1, 2, 3].map((i) => (
              <div key={i} className="h-20 rounded-xl animate-shimmer" />
            ))}
        </div>
      )}

      {/* Detail view */}
      {detail && !detailLoading && (
        <div className="animate-fade-in">
          {/* Back button */}
          <button
            onClick={handleBack}
            className="text-[12px] font-medium text-indigo-600 hover:text-indigo-700 mb-5 inline-flex items-center gap-1.5 transition-colors"
          >
            <svg
              className="w-3.5 h-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18"
              />
            </svg>
            Zurück zur Liste
          </button>

          {/* Header card with gradient */}
          <div className="rounded-2xl border border-[var(--border)] bg-white overflow-hidden card-shadow mb-6">
            <div className="bg-gradient-to-r from-indigo-500 to-purple-500 px-6 py-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-white/90 text-[11px] font-semibold px-2.5 py-1 rounded-md bg-white/20 backdrop-blur-sm">
                  {getModuleLabel(detail.module)}
                </span>
                <span className="text-white/70 text-[12px]">
                  {new Date(detail.created_at).toLocaleDateString("de-DE", {
                    day: "2-digit",
                    month: "long",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
              <h2 className="text-white text-[20px] font-bold">
                {MODULE_TITLES[detail.module] || getModuleLabel(detail.module)}
              </h2>
            </div>
          </div>

          {/* Hard Facts */}
          <HardFacts rawData={detail.raw_data} />

          {/* AI Analysis content */}
          <div className="rounded-2xl border border-[var(--border)] bg-white p-6 md:p-8 card-shadow">
            <h3 className="text-[14px] font-bold text-[var(--text-primary)] mb-5 pb-4 border-b border-[var(--border)] flex items-center gap-2">
              <svg
                className="w-4 h-4 text-indigo-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z"
                />
              </svg>
              KI-Analyse
            </h3>
            <div className="prose-report">
              <ReactMarkdown>{detail.content_md}</ReactMarkdown>
            </div>
          </div>
        </div>
      )}

      {/* List view */}
      {!detail && !detailLoading && !loading && (
        <div>
          {reports.length === 0 ? (
            <div className="rounded-xl border border-dashed border-[var(--border)] bg-[var(--bg-secondary)] p-8 text-center">
              <div className="w-12 h-12 rounded-xl bg-indigo-50 flex items-center justify-center mx-auto mb-3">
                <svg
                  className="w-6 h-6 text-indigo-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
                  />
                </svg>
              </div>
              <p className="text-[13px] font-medium text-[var(--text-primary)]">
                Noch keine Reports
              </p>
              <p className="text-[12px] text-[var(--text-muted)] mt-1">
                Generiere deinen ersten Report über die Module-Seite.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {reports.map((r) => (
                <ReportCard
                  key={r.id}
                  id={r.id}
                  module={r.module}
                  created_at={r.created_at}
                  preview={stripMarkdownPreview(r.content_md, 150)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </DashboardShell>
  );
}

export default function ReportsPage() {
  return (
    <Suspense>
      <ReportsContent />
    </Suspense>
  );
}
