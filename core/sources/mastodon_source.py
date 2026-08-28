"""Mastodon: Öffentliche Posts via Instance-API durchsuchen."""

import logging
from datetime import UTC, datetime

import httpx

from core.events import NormalizedEvent

log = logging.getLogger(__name__)

# Große deutschsprachige Instanzen
MASTODON_INSTANCES = [
    "https://mastodon.social",
    "https://mastodon.online",
    "https://troet.cafe",
]


async def fetch_mastodon_mentions(company_name: str, limit: int = 15) -> list[NormalizedEvent]:
    """Sucht öffentliche Mastodon-Posts über mehrere Instanzen.

    Keine Authentifizierung nötig – nutzt die öffentliche Search API.
    """
    events: list[NormalizedEvent] = []
    seen_urls: set[str] = set()

    async with httpx.AsyncClient(timeout=12.0) as client:
        for instance in MASTODON_INSTANCES:
            try:
                resp = await client.get(
                    f"{instance}/api/v2/search",
                    params={
                        "q": company_name,
                        "type": "statuses",
                        "limit": min(limit, 40),
                    },
                )
                if resp.status_code != 200:
                    continue
                statuses = resp.json().get("statuses", [])
            except (httpx.HTTPError, Exception) as e:
                log.debug("Mastodon %s fehlgeschlagen: %s", instance, e)
                continue

            for status in statuses:
                url = status.get("url") or status.get("uri", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # HTML-Tags entfernen
                content = _strip_html(status.get("content", ""))
                account = status.get("account", {})
                display_name = account.get("display_name") or account.get("username", "")
                acct = account.get("acct", "")

                created = status.get("created_at", "")
                try:
                    ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    ts = datetime.now(UTC)

                favourites = status.get("favourites_count", 0)
                reblogs = status.get("reblogs_count", 0)
                replies = status.get("replies_count", 0)

                events.append(NormalizedEvent(
                    source="mastodon",
                    event_type="post",
                    title=f"Mastodon: {content[:80]}",
                    description=content[:500],
                    url=url,
                    timestamp=ts,
                    raw_data={
                        "platform": "mastodon",
                        "author": acct or display_name,
                        "display_name": display_name,
                        "score": favourites + reblogs,
                        "num_comments": replies,
                        "favourites": favourites,
                        "reblogs": reblogs,
                        "instance": instance,
                    },
                ))

            if len(events) >= limit:
                break

    # Nach Engagement sortieren
    events.sort(key=lambda e: e.raw_data.get("score", 0) + e.raw_data.get("num_comments", 0), reverse=True)
    events = events[:limit]

    log.info("Mastodon: %d Posts für '%s'", len(events), company_name)
    return events


def _strip_html(html: str) -> str:
    """Einfache HTML-Tag-Entfernung."""
    import re
    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    return text.strip()
