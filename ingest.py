#!/usr/bin/env python3
"""Data Ingestion Pipeline: Holt Daten aus allen Quellen und verarbeitet sie zu Events."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.database import get_session, init_db
from core.event_store import (
    get_event_stats,
    load_content_hashes,
    load_known_dedup_keys,
    save_content_hash,
    store_events,
)
from core.events import IMPORTANCE_THRESHOLD, EventEngine
from core.sources.cve_source import CVESource
from core.sources.github_source import GitHubSource
from core.sources.rss_source import RSSSource
from core.sources.web_scraper import WebScraperSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ingest")


async def run_ingestion():
    """Führt die gesamte Ingestion Pipeline aus."""
    init_db()

    # 1. Engine vorbereiten – bekannte Events laden für Dedup
    with get_session() as db:
        known_keys = load_known_dedup_keys(db)
        content_hashes = load_content_hashes(db)

    engine = EventEngine()
    engine.load_seen_keys(known_keys)

    log.info("Pipeline gestartet. %d bekannte Events in DB.", len(known_keys))

    # 2. Datenquellen konfigurieren
    sources = [
        GitHubSource(repos=[
            "fastapi/fastapi",
            "pydantic/pydantic",
            "encode/httpx",
            "pallets/flask",
            "django/django",
        ]),
        CVESource(keywords=["python", "fastapi", "django"], days_back=14),
        RSSSource(),
        WebScraperSource(known_hashes=content_hashes),
    ]

    # 3. Daten parallel abrufen
    all_events = []
    for source in sources:
        log.info("Fetching: %s...", source.name)
        try:
            events = await source.fetch()
            all_events.extend(events)
            log.info("  → %d Events von %s", len(events), source.name)
        except Exception:
            log.exception("Fehler bei Source %s", source.name)

    log.info("Total: %d rohe Events von %d Quellen", len(all_events), len(sources))

    # 4. Engine: Score + Deduplizieren
    processed = engine.process(all_events)
    important = engine.get_important(processed)

    # 5. In DB speichern
    with get_session() as db:
        stored = store_events(db, processed)

        # Content-Hashes aktualisieren (für Web-Scraper)
        scraper_source = next((s for s in sources if isinstance(s, WebScraperSource)), None)
        if scraper_source:
            for url, hash_val in scraper_source.known_hashes.items():
                save_content_hash(db, url, hash_val)

    # 6. Ergebnis anzeigen
    print(f"\n{'='*70}")
    print("INGESTION COMPLETE")
    print(f"{'='*70}")
    print(f"  Rohe Events:       {len(all_events)}")
    print(f"  Nach Dedup:        {len(processed)}")
    print(f"  Neu gespeichert:   {stored}")
    print(f"  Davon important:   {len(important)} (score >= {IMPORTANCE_THRESHOLD})")

    if important:
        print(f"\n{'─'*70}")
        print("TOP EVENTS (nach Relevanz)")
        print(f"{'─'*70}")
        for e in important[:15]:
            sev_icon = {"high": "!!!", "medium": " !!", "low": "  !"}[e.severity]
            print(f"  [{e.relevance_score:3d}] {sev_icon} [{e.source:6s}] {e.title[:70]}")
            print(f"         {e.url[:80]}")

    # Stats
    with get_session() as db:
        stats = get_event_stats(db)

    print(f"\n{'─'*70}")
    print("DB STATS")
    print(f"{'─'*70}")
    print(f"  Total Events:      {stats['total_events']}")
    print(f"  By Source:         {stats['by_source']}")
    print(f"  By Severity:       {stats['by_severity']}")
    print(f"  Avg Score:         {stats['avg_relevance_score']}")
    print()


if __name__ == "__main__":
    asyncio.run(run_ingestion())
