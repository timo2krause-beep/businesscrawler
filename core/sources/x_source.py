"""X/Twitter Source: Sucht Tweets via Nitter RSS oder Web-Scraping Fallback."""

import logging
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

import httpx

from core.events import NormalizedEvent

log = logging.getLogger(__name__)

# Nitter-Instanzen (werden der Reihe nach probiert)
NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.woodland.cafe",
]


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_rss_date(date_str: str) -> datetime:
    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError:
            continue
    return datetime.now(UTC)


async def _try_nitter_search(client: httpx.AsyncClient, instance: str, query: str, limit: int) -> list[NormalizedEvent]:
    """Versucht Tweets via Nitter RSS-Suche zu holen."""
    url = f"{instance}/search/rss"
    try:
        resp = await client.get(url, params={"f": "tweets", "q": query}, timeout=10.0)
        resp.raise_for_status()
    except httpx.HTTPError:
        return []

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError:
        return []

    events = []
    items = root.findall(".//item")[:limit]

    for item in items:
        title = _strip_html(item.findtext("title", ""))
        link = item.findtext("link", "")
        pub_date = item.findtext("pubDate", "")
        creator = item.findtext("{http://purl.org/dc/elements/1.1/}creator", "")
        description = _strip_html(item.findtext("description", ""))[:500]

        # Nitter-Links in Twitter-Links umwandeln
        if link:
            for inst in NITTER_INSTANCES:
                link = link.replace(inst, "https://x.com")

        ts = _parse_rss_date(pub_date) if pub_date else datetime.now(UTC)

        events.append(NormalizedEvent(
            source="x_twitter",
            event_type="social_mention",
            title=f"X: {title[:120]}",
            description=description or title,
            url=link,
            timestamp=ts,
            raw_data={
                "platform": "x_twitter",
                "author": creator.replace("@", ""),
                "full_text": description,
            },
        ))

    return events


async def fetch_x_mentions(
    company_name: str,
    limit: int = 20,
) -> list[NormalizedEvent]:
    """Sucht X/Twitter nach Erwähnungen via Nitter-Instanzen."""
    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=True,
    ) as client:
        for instance in NITTER_INSTANCES:
            events = await _try_nitter_search(client, instance, company_name, limit)
            if events:
                log.info("X/Twitter via %s: %d Tweets für '%s'", instance, len(events), company_name)
                return events
            log.debug("Nitter-Instanz %s liefert keine Ergebnisse", instance)

    log.warning("X/Twitter: Keine Nitter-Instanz verfügbar für '%s'", company_name)
    return []
