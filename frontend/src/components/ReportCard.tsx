"use client";

import Link from "next/link";
import { getModuleLabel } from "@/lib/modules";
import { MODULE_INFO } from "@/lib/modules";

interface Props {
  id: number;
  module: string;
  created_at: string;
  preview?: string;
}

const BADGE_COLORS: Record<string, string> = {
  blue:    "text-blue-700 bg-blue-50",
  purple:  "text-purple-700 bg-purple-50",
  orange:  "text-orange-700 bg-orange-50",
  emerald: "text-emerald-700 bg-emerald-50",
  pink:    "text-pink-700 bg-pink-50",
  cyan:    "text-cyan-700 bg-cyan-50",
  amber:   "text-amber-700 bg-amber-50",
};

export default function ReportCard({ id, module, created_at, preview }: Props) {
  const date = new Date(created_at);
  const formatted = date.toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  const info = MODULE_INFO[module];
  const badgeColor = BADGE_COLORS[info?.color || "blue"] || BADGE_COLORS.blue;

  return (
    <Link
      href={`/reports?id=${id}`}
      className="block rounded-xl border border-[var(--border)] bg-white p-4 hover:border-[var(--border-light)] hover:shadow-sm transition-all duration-200 card-shadow"
    >
      <div className="flex items-center justify-between">
        <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-md ${badgeColor}`}>
          {getModuleLabel(module)}
        </span>
        <span className="text-[11px] text-[var(--text-muted)]">{formatted}</span>
      </div>
      {preview && (
        <p className="mt-2.5 text-[12px] text-[var(--text-secondary)] line-clamp-2 leading-relaxed">
          {preview}
        </p>
      )}
    </Link>
  );
}
