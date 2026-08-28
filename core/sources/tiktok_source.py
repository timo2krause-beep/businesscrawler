"""TikTok Source: Scraped öffentliche Suchergebnisse."""

import json
import logging
import re
from datetime import UTC, datetime

import httpx

from core.events import NormalizedEvent

log = logging.getLogger(__name__)

TIKTOK_SEARCH_URL = "https://www.tiktok.com/api/search/general/full/"


async def _scrape_tiktok_search(client: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
    """Scraped TikTok-Suchergebnisse über die interne API."""
    try:
        resp = await client.get(
            TIKTOK_SEARCH_URL,
            params={
                "keyword": query,
                "offset": 0,
                "search_source": "normal_search",
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])[:limit]
    except (httpx.HTTPError, json.JSONDecodeError, KeyError):
        return []


async def _scrape_tiktok_web(client: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
    """Fallback: Scraped TikTok-Websuche und extrahiert Video-Infos aus dem HTML."""
    try:
        resp = await client.get(
            "https://www.tiktok.com/search",
            params={"q": query},
            timeout=15.0,
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        log.debug("TikTok Web-Scraping fehlgeschlagen: %s", e)
        return []

    # Versuche SIGI_STATE oder universalData aus dem HTML zu extrahieren
    results = []
    patterns = [
        r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.+?)</script>',
        r'<script id="SIGI_STATE"[^>]*>(.+?)</script>',
    ]

    for pattern in patterns:
        match = re.search(pattern, resp.text, re.DOTALL)
        if not match:
            continue
        try:
            state = json.loads(match.group(1))
            # Navigiere durch die verschachtelte Struktur
            items = (
                state.get("__DEFAULT_SCOPE__", {})
                .get("webapp.search-page", {})
                .get("searchResult", {})
                .get("data", [])
            )
            if not items:
                # Alternative Struktur
                items = list(state.get("ItemModule", {}).values())

            for item in items[:limit]:
                video = item.get("item", item) if isinstance(item, dict) else {}
                results.append(video)

            if results:
                break
        except (json.JSONDecodeError, AttributeError):
            continue

    return results


async def fetch_tiktok_mentions(
    company_name: str,
    limit: int = 15,
) -> list[NormalizedEvent]:
    """Sucht TikTok nach Erwähnungen eines Unternehmens."""
    events = []

    async with httpx.AsyncClient(
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        },
        follow_redirects=True,
    ) as client:
        # Erst API versuchen, dann Web-Scraping
        raw_results = await _scrape_tiktok_search(client, company_name, limit)
        if not raw_results:
            raw_results = await _scrape_tiktok_web(client, company_name, limit)

    for item in raw_results:
        if not isinstance(item, dict):
            continue

        desc = item.get("desc", "") or item.get("title", "")
        if not desc:
            continue

        author_info = item.get("author", {})
        author = author_info.get("uniqueId", "") if isinstance(author_info, dict) else str(author_info)
        stats = item.get("stats", {})
        video_id = item.get("id", "")

        play_count = stats.get("playCount", 0) if isinstance(stats, dict) else 0
        like_count = stats.get("diggCount", 0) or stats.get("likeCount", 0) if isinstance(stats, dict) else 0
        comment_count = stats.get("commentCount", 0) if isinstance(stats, dict) else 0
        share_count = stats.get("shareCount", 0) if isinstance(stats, dict) else 0

        created = item.get("createTime", 0)
        ts = datetime.fromtimestamp(int(created), tz=UTC) if created else datetime.now(UTC)

        url = f"https://www.tiktok.com/@{author}/video/{video_id}" if author and video_id else ""

        events.append(NormalizedEvent(
            source="tiktok",
            event_type="social_mention",
            title=f"TikTok: {desc[:100]}",
            description=desc[:500],
            url=url,
            timestamp=ts,
            raw_data={
                "platform": "tiktok",
                "author": author,
                "play_count": play_count,
                "like_count": like_count,
                "comment_count": comment_count,
                "share_count": share_count,
                "score": play_count,  # Für einheitliches Engagement-Sorting
            },
        ))

    log.info("TikTok: %d Videos für '%s' gefunden", len(events), company_name)
    return events
