"""RSS Data Source: Liest Feeds und erzeugt Events pro Entry."""

import logging
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from core.events import NormalizedEvent
from core.sources.base import BaseSource

log = logging.getLogger(__name__)

DEFAULT_FEEDS = [
    ("https://blog.python.org/feeds/posts/default?alt=rss", "Python Blog"),
    ("https://blog.rust-lang.org/feed.xml", "Rust Blog"),
    ("https://hnrss.org/newest?q=python+release&count=20", "HN Python"),
]

TAG_RE = re.compile(r"<[^>]+>")


class RSSSource(BaseSource):
    name = "rss"

    def __init__(self, feeds: list[tuple[str, str]] | None = None):
        self.feeds = feeds or DEFAULT_FEEDS

    async def fetch(self) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []

        async with httpx.AsyncClient(
            timeout=15.0,
            headers={"User-Agent": "Mozilla/5.0 (ScraperPlatform/1.0)"},
            follow_redirects=True,
        ) as client:
            for url, feed_name in self.feeds:
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    feed = feedparser.parse(resp.text)

                    if not feed.entries:
                        log.warning("RSS Feed leer: %s", feed_name)
                        continue

                    for entry in feed.entries[:20]:
                        events.append(self._entry_to_event(entry, feed_name))

                    log.info("RSS: %d entries von '%s'", min(20, len(feed.entries)), feed_name)

                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    log.warning("RSS HTTP-Fehler bei '%s': %s", feed_name, e)
                except Exception as e:
                    log.warning("RSS Fehler bei '%s': %s", feed_name, e)

        return events

    def _entry_to_event(self, entry: dict, feed_name: str) -> NormalizedEvent:
        ts = datetime.now(UTC)
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                ts = datetime(*entry.published_parsed[:6], tzinfo=UTC)
            except (TypeError, ValueError):
                pass
        elif hasattr(entry, "published") and entry.published:
            try:
                ts = parsedate_to_datetime(entry.published)
            except (TypeError, ValueError):
                pass

        summary = entry.get("summary", entry.get("description", ""))
        clean_summary = TAG_RE.sub("", summary)[:500]

        return NormalizedEvent(
            source="rss",
            event_type="article",
            title=entry.get("title", "Unbekannt"),
            description=clean_summary,
            url=entry.get("link", ""),
            timestamp=ts,
            raw_data={
                "feed_name": feed_name,
                "author": entry.get("author", ""),
                "tags": [t.get("term", "") for t in entry.get("tags", [])],
            },
        )
