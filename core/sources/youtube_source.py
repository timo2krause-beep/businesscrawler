"""YouTube: Video-Suche und Kommentare via YouTube Data API v3."""

import logging
from datetime import UTC, datetime

import httpx

from config.settings import settings
from core.events import NormalizedEvent

log = logging.getLogger(__name__)

YOUTUBE_API = "https://www.googleapis.com/youtube/v3"


async def fetch_youtube_mentions(company_name: str, limit: int = 15) -> list[NormalizedEvent]:
    """Sucht YouTube-Videos und liest Top-Kommentare.

    Nutzt den gleichen Google API Key wie Places API.
    YouTube Data API v3 muss im Google Cloud Projekt aktiviert sein.
    """
    api_key = settings.google_places_api_key
    if not api_key:
        log.warning("Google API Key nicht konfiguriert – überspringe YouTube")
        return []

    events: list[NormalizedEvent] = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1) Video-Suche
        try:
            resp = await client.get(
                f"{YOUTUBE_API}/search",
                params={
                    "part": "snippet",
                    "q": company_name,
                    "type": "video",
                    "order": "date",
                    "maxResults": min(limit, 25),
                    "relevanceLanguage": "de",
                    "key": api_key,
                },
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
        except httpx.HTTPError as e:
            log.warning("YouTube-Suche fehlgeschlagen: %s", e)
            return []

        for item in items:
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId", "")
            if not video_id:
                continue

            title = snippet.get("title", "")
            description = snippet.get("description", "")
            channel = snippet.get("channelTitle", "")
            published = snippet.get("publishedAt", "")

            try:
                ts = datetime.fromisoformat(published.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                ts = datetime.now(UTC)

            video_url = f"https://www.youtube.com/watch?v={video_id}"

            # Kommentare für dieses Video holen
            comments = await _fetch_comments(client, video_id, api_key, max_comments=3)

            events.append(NormalizedEvent(
                source="youtube",
                event_type="video",
                title=f"YouTube: {title}",
                description=description[:500],
                url=video_url,
                timestamp=ts,
                raw_data={
                    "platform": "youtube",
                    "video_id": video_id,
                    "channel": channel,
                    "author": channel,
                    "comments": comments,
                    "comment_count": len(comments),
                    "score": 0,
                    "num_comments": len(comments),
                },
            ))

    log.info("YouTube: %d Videos für '%s'", len(events), company_name)
    return events


async def _fetch_comments(client: httpx.AsyncClient, video_id: str, api_key: str, max_comments: int = 3) -> list[dict]:
    """Holt Top-Kommentare für ein Video."""
    try:
        resp = await client.get(
            f"{YOUTUBE_API}/commentThreads",
            params={
                "part": "snippet",
                "videoId": video_id,
                "order": "relevance",
                "maxResults": max_comments,
                "key": api_key,
            },
        )
        if resp.status_code == 403:
            return []  # Kommentare deaktiviert
        resp.raise_for_status()

        comments = []
        for item in resp.json().get("items", []):
            top = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            comments.append({
                "author": top.get("authorDisplayName", ""),
                "text": top.get("textDisplay", "")[:300],
                "likes": top.get("likeCount", 0),
            })
        return comments
    except httpx.HTTPError:
        return []
