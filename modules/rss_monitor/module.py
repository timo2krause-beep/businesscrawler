"""RSS Monitor: Überwacht Tech-Blogs und News-Feeds."""

from core.base_module import BaseModule, Report, ReportItem
from core.events import score_event
from core.sources.rss_source import DEFAULT_FEEDS, RSSSource


class RSSMonitor(BaseModule):
    name = "rss_monitor"
    description = "Überwacht Tech-Blogs und News-Feeds via RSS"

    def __init__(self, feeds: list[tuple[str, str]] | None = None):
        self.feeds = feeds or DEFAULT_FEEDS

    async def fetch_data(self) -> list[dict]:
        source = RSSSource(feeds=self.feeds)
        events = await source.fetch()
        for e in events:
            score_event(e)
        return [
            {
                "title": e.title,
                "description": e.description,
                "url": e.url,
                "score": e.relevance_score,
                "timestamp": e.timestamp.isoformat(),
                **e.raw_data,
            }
            for e in events
        ]

    def process_data(self, raw_data: list[dict]) -> list[ReportItem]:
        items = []
        for entry in raw_data:
            items.append(ReportItem(
                title=entry["title"],
                category="info",
                summary=entry["description"][:300],
                source_url=entry["url"],
                metadata={"feed": entry.get("feed_name"), "relevance": entry.get("score", 45)},
            ))
        return items

    def generate_report(self, items: list[ReportItem]) -> Report:
        return Report(
            module_name=self.name,
            title="RSS News Monitor – Wochenbericht",
            items=items,
        )
