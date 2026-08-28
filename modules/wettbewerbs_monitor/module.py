"""Wettbewerbs-Monitor: Scraped Webseiten und erkennt Änderungen mit Diff-Anzeige."""

from core.base_module import BaseModule, Report, ReportItem
from core.database import get_session
from core.event_store import load_content_hashes, load_content_texts, save_content_hash
from core.events import score_event
from core.sources.web_scraper import DEFAULT_TARGETS, ScrapingTarget, WebScraperSource


class WettbewerbsMonitor(BaseModule):
    name = "wettbewerbs_monitor"
    description = "Scraped Wettbewerber-Webseiten und erkennt Änderungen"

    def __init__(self, targets: list[ScrapingTarget] | None = None):
        self.targets = targets or DEFAULT_TARGETS

    async def fetch_data(self) -> list[dict]:
        # Content-Hashes und Texte aus DB laden für Diff-Erkennung
        with get_session() as db:
            known_hashes = load_content_hashes(db)
            known_content = load_content_texts(db)

        source = WebScraperSource(
            targets=self.targets,
            known_hashes=known_hashes,
            known_content=known_content,
        )
        events = await source.fetch()

        # Aktualisierte Hashes + Content zurück in DB speichern
        with get_session() as db:
            for url, text in source.updated_content.items():
                new_hash = source.known_hashes.get(url, "")
                save_content_hash(db, url, new_hash, content_text=text)
            db.commit()

        for e in events:
            score_event(e)

        return [
            {
                "title": e.title,
                "description": e.description,
                "url": e.url,
                "score": e.relevance_score,
                "event_type": e.event_type,
                "timestamp": e.timestamp.isoformat(),
                **e.raw_data,
            }
            for e in events
        ]

    def process_data(self, raw_data: list[dict]) -> list[ReportItem]:
        items = []
        for entry in raw_data:
            is_baseline = entry.get("is_baseline", False)
            is_error = entry.get("event_type") == "error"

            if is_error:
                category = "warning"
            elif is_baseline:
                category = "info"
            else:
                category = "important"

            items.append(ReportItem(
                title=entry["title"],
                category=category,
                summary=entry["description"][:500],
                source_url=entry["url"],
                metadata={
                    "content_hash": entry.get("content_hash"),
                    "old_hash": entry.get("old_hash"),
                    "event_type": entry.get("event_type"),
                    "diff": entry.get("diff"),
                    "relevance": entry.get("score", 0),
                },
            ))
        return items

    def generate_report(self, items: list[ReportItem]) -> Report:
        return Report(
            module_name=self.name,
            title="Wettbewerbs-Monitor – Änderungsbericht",
            items=items,
        )
