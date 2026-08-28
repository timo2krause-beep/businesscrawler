"""Google News Source: RSS-Feed für Unternehmens-News."""

import logging
import re
from datetime import UTC, datetime

import httpx

from core.events import NormalizedEvent

log = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_rss_date(date_str: str) -> datetime:
    """Parst RFC 2822 / RFC 822 Datumsformat."""
    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return datetime.now(UTC)


async def fetch_googlenews_mentions(
    company_name: str,
    language: str = "de",
    limit: int = 20,
) -> list[NormalizedEvent]:
    """Holt aktuelle News via Google News RSS."""
    events = []

    params = {
        "q": company_name,
        "hl": language,
        "gl": "DE" if language == "de" else "US",
        "ceid": f"DE:{language}" if language == "de" else f"US:{language}",
    }

    async with httpx.AsyncClient(
        timeout=15.0,
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=True,
    ) as client:
        try:
            resp = await client.get(GOOGLE_NEWS_RSS, params=params)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("Google News RSS fehlgeschlagen: %s", e)
            return []

    # Einfaches XML-Parsing ohne lxml-Dependency
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        log.warning("Google News RSS Parse-Fehler: %s", e)
        return []

    items = root.findall(".//item")[:limit]

    for item in items:
        title = _strip_html(item.findtext("title", ""))
        link = item.findtext("link", "")
        pub_date = item.findtext("pubDate", "")
        source_name = item.findtext("source", "")
        description = _strip_html(item.findtext("description", ""))[:500]

        ts = _parse_rss_date(pub_date) if pub_date else datetime.now(UTC)

        events.append(NormalizedEvent(
            source="googlenews",
            event_type="news_mention",
            title=f"News: {title}",
            description=description or title,
            url=link,
            timestamp=ts,
            raw_data={
                "platform": "googlenews",
                "source_name": source_name,
                "pub_date": pub_date,
            },
        ))

    log.info("Google News: %d Artikel für '%s' gefunden", len(events), company_name)
    return events
