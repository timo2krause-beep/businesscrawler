export const MODULE_INFO: Record<
  string,
  {
    label: string;
    description: string;
    icon: string;
    color: string;
    visible?: boolean;
    category?: "marketing" | "tech";
    pref_key?: string;
    pref_label?: string;
    pref_placeholder?: string;
    pref_type?: string;
  }
> = {
  tech_stack_monitor: {
    label: "Tech-Stack Monitor",
    description:
      "Überwacht GitHub Releases und Framework-Updates. Erkennt neue Versionen, Breaking Changes und Sicherheitslücken.",
    icon: "code",
    color: "blue",
    visible: true,
    category: "tech",
    pref_key: "watched_repos",
    pref_label: "Überwachte Repositories",
    pref_placeholder: "owner/repo (z.B. vercel/next.js)",
  },
  cve_monitor: {
    label: "CVE Security Monitor",
    description:
      "Durchsucht die NVD-Datenbank nach Sicherheitslücken. Filtert nach Severity und relevanten Keywords.",
    icon: "shield",
    color: "purple",
    visible: true,
    category: "tech",
    pref_key: "cve_keywords",
    pref_label: "Überwachte Keywords",
    pref_placeholder: "Keyword (z.B. react, nginx, openssl)",
  },
  rss_monitor: {
    label: "RSS News Monitor",
    description:
      "Überwacht Tech-Blogs und News-Feeds via RSS/Atom. Sammelt relevante Artikel automatisch.",
    icon: "rss",
    color: "orange",
    visible: true,
    category: "tech",
    pref_key: "rss_feeds",
    pref_label: "RSS Feeds",
    pref_placeholder: "Feed-URL (z.B. https://blog.example.com/feed)",
  },
  wettbewerbs_monitor: {
    label: "Webseiten-Monitor",
    description:
      "Überwacht Wettbewerber-Webseiten auf Änderungen und erkennt Preisänderungen, neue Features und strategische Updates.",
    icon: "chart",
    color: "emerald",
    visible: true,
    category: "marketing",
    pref_key: "scraping_targets",
    pref_label: "Überwachte Webseiten",
    pref_placeholder: "URL",
    pref_type: "targets",
  },
  ki_wettbewerb: {
    label: "KI-Wettbewerbsanalyse",
    description:
      "Identifiziert automatisch Wettbewerber per KI, erstellt detaillierte Profile und überwacht deren Online-Aktivitäten.",
    icon: "brain",
    color: "pink",
    visible: true,
    category: "marketing",
    pref_type: "competitors",
  },
  social_media_generator: {
    label: "Social-Media-Vorlagen",
    description:
      "Erstellt fertige, sofort postbare Instagram/Facebook-Vorlagen aus deiner Wettbewerbsanalyse – inkl. Hashtags und Bildidee.",
    icon: "chat",
    color: "purple",
    visible: true,
    category: "marketing",
    pref_type: "company",
  },
  social_sentiment: {
    label: "Social Sentiment",
    description:
      "Analysiert die Stimmung auf Reddit, YouTube, Mastodon, X/Twitter, TikTok, Hacker News und Google News. Erstellt KI-basierte Sentiment-Reports.",
    icon: "chat",
    color: "cyan",
    visible: true,
    category: "marketing",
    pref_type: "company",
  },
  review_monitor: {
    label: "Bewertungs-Monitor",
    description:
      "Sammelt und analysiert Bewertungen von Google, Trustpilot, Tripadvisor, Jameda, Kununu, ProvenExpert, Trusted Shops und weiteren branchenrelevanten Plattformen.",
    icon: "star",
    color: "amber",
    visible: true,
    category: "marketing",
    pref_type: "company",
  },
};

/** Only modules marked visible for the marketing platform */
export const VISIBLE_MODULES = Object.keys(MODULE_INFO).filter(
  (k) => MODULE_INFO[k].visible !== false
);

/** Sichtbare Module einer Kategorie, in Einfügereihenfolge. */
export function getModulesByCategory(category: "marketing" | "tech"): string[] {
  return VISIBLE_MODULES.filter((k) => (MODULE_INFO[k].category || "marketing") === category);
}

export function getModuleLabel(name: string): string {
  return MODULE_INFO[name]?.label || name;
}
