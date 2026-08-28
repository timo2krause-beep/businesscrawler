"""Hacker News Source: Sucht Beiträge via Algolia Search API."""

import logging
from datetime import UTC, datetime

import httpx

from core.events import NormalizedEvent

log = logging.getLogger(__name__)

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"


async def fetch_hackernews_mentions(
    company_name: str,
    limit: int = 20,
) -> list[NormalizedEvent]:
    """Sucht Hacker News nach Erwähnungen eines Unternehmens."""
    events = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                HN_SEARCH_URL,
                params={
                    "query": company_name,
                    "tags": "(story,show_hn,ask_hn)",
                    "hitsPerPage": limit,
                },
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("HN-Suche fehlgeschlagen: %s", e)
            return []

        data = resp.json()
        hits = data.get("hits", [])

        for hit in hits:
            title = hit.get("title", "")
            author = hit.get("author", "")
            points = hit.get("points", 0) or 0
            num_comments = hit.get("num_comments", 0) or 0
            object_id = hit.get("objectID", "")
            created_at = hit.get("created_at", "")

            url = f"https://news.ycombinator.com/item?id={object_id}" if object_id else ""

            try:
                ts = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                ts = datetime.now(UTC)

            story_url = hit.get("url", "")
            description = title
            if story_url:
                description = f"{title}\n{story_url}"

            events.append(NormalizedEvent(
                source="hackernews",
                event_type="social_mention",
                title=f"HN: {title}",
                description=description,
                url=url,
                timestamp=ts,
                raw_data={
                    "platform": "hackernews",
                    "author": author,
                    "points": points,
                    "num_comments": num_comments,
                    "story_url": story_url,
                },
            ))

    log.info("HN: %d Stories für '%s' gefunden", len(events), company_name)
    return events
