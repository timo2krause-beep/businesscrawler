"""Unified Event Model und Processing Engine."""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime

log = logging.getLogger(__name__)


@dataclass
class NormalizedEvent:
    """Einheitliches Datenformat für alle Quellen."""
    source: str           # github | cve | rss | scrape
    event_type: str       # release | vulnerability | article | price_change
    title: str
    description: str
    url: str
    timestamp: datetime
    raw_data: dict = field(default_factory=dict)
    relevance_score: int = 0    # 0–100, wird von der Engine berechnet
    severity: str = "low"       # low | medium | high
    dedup_key: str = ""         # Wird automatisch generiert

    def __post_init__(self):
        if not self.dedup_key:
            self.dedup_key = self._generate_dedup_key()

    def _generate_dedup_key(self) -> str:
        """Einzigartiger Key zur Deduplizierung."""
        raw = f"{self.source}:{self.event_type}:{self.url}:{self.title}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


# --- Scoring Rules ---

SCORING_RULES: list[dict] = [
    # GitHub
    {"source": "github", "event_type": "release", "field": "is_major", "value": True,
     "score": 90, "severity": "high"},
    {"source": "github", "event_type": "release", "field": "is_minor", "value": True,
     "score": 75, "severity": "medium"},
    {"source": "github", "event_type": "release", "field": None, "value": None,
     "score": 50, "severity": "low"},
    {"source": "github", "event_type": "security_advisory",
     "field": None, "value": None, "score": 85, "severity": "high"},

    # CVE
    {"source": "cve", "event_type": "vulnerability", "field": "cvss_severity", "value": "CRITICAL",
     "score": 100, "severity": "high"},
    {"source": "cve", "event_type": "vulnerability", "field": "cvss_severity", "value": "HIGH",
     "score": 90, "severity": "high"},
    {"source": "cve", "event_type": "vulnerability", "field": "cvss_severity", "value": "MEDIUM",
     "score": 70, "severity": "medium"},
    {"source": "cve", "event_type": "vulnerability", "field": "cvss_severity", "value": "LOW",
     "score": 40, "severity": "low"},

    # RSS
    {"source": "rss", "event_type": "article", "field": None, "value": None,
     "score": 45, "severity": "low"},

    # Scraping
    {"source": "scrape", "event_type": "price_change", "field": None, "value": None,
     "score": 85, "severity": "high"},
    {"source": "scrape", "event_type": "feature_change", "field": None, "value": None,
     "score": 70, "severity": "medium"},
]

IMPORTANCE_THRESHOLD = 50  # Events mit score >= 50 gelten als "important"


def score_event(event: NormalizedEvent) -> NormalizedEvent:
    """Bewertet ein Event anhand der Scoring Rules."""
    best_score = 30  # Default
    best_severity = "low"

    for rule in SCORING_RULES:
        if rule["source"] != event.source:
            continue
        if rule["event_type"] != event.event_type:
            continue

        # Feld-spezifischer Match
        if rule["field"] is not None:
            actual = event.raw_data.get(rule["field"])
            if actual != rule["value"]:
                continue

        if rule["score"] > best_score:
            best_score = rule["score"]
            best_severity = rule["severity"]

    event.relevance_score = best_score
    event.severity = best_severity
    return event


def is_important(event: NormalizedEvent) -> bool:
    return event.relevance_score >= IMPORTANCE_THRESHOLD


# --- Event Processing Engine ---

class EventEngine:
    """Verarbeitet rohe Daten zu bewerteten, deduplizierten Events."""

    def __init__(self):
        self._seen_keys: set[str] = set()

    def load_seen_keys(self, keys: set[str]) -> None:
        """Lädt bereits bekannte dedup_keys (z.B. aus der DB)."""
        self._seen_keys = keys

    def process(self, events: list[NormalizedEvent]) -> list[NormalizedEvent]:
        """Score → Deduplicate → Filter."""
        result = []

        for event in events:
            # 1. Score berechnen
            score_event(event)

            # 2. Deduplizieren
            if event.dedup_key in self._seen_keys:
                log.debug("Duplikat übersprungen: %s", event.title[:60])
                continue
            self._seen_keys.add(event.dedup_key)

            # 3. In Ergebnis aufnehmen
            result.append(event)

        important = [e for e in result if is_important(e)]
        log.info(
            "EventEngine: %d input → %d nach dedup → %d important (score >= %d)",
            len(events), len(result), len(important), IMPORTANCE_THRESHOLD,
        )

        return result

    def get_important(self, events: list[NormalizedEvent]) -> list[NormalizedEvent]:
        """Nur Events über dem Schwellwert."""
        return sorted(
            [e for e in events if is_important(e)],
            key=lambda e: e.relevance_score,
            reverse=True,
        )
