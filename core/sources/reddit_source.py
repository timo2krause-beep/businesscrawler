"""Reddit Source: Sucht Posts und Kommentare zu einem Unternehmen via öffentliche JSON API."""

import logging
from datetime import UTC, datetime

import httpx

from core.events import NormalizedEvent

log = logging.getLogger(__name__)

REDDIT_SEARCH_URL = "https://www.reddit.com/search.json"


async def fetch_reddit_mentions(
    company_name: str,
    limit: int = 25,
    sort: str = "new",
    time_filter: str = "week",
) -> list[NormalizedEvent]:
    """Sucht Reddit nach Erwähnungen eines Unternehmens."""
    events = []

    async with httpx.AsyncClient(
        timeout=15.0,
        headers={
            "User-Agent": "ScrapeBot/1.0 (Competitive Intelligence Tool)",
        },
    ) as client:
        try:
            resp = await client.get(
                REDDIT_SEARCH_URL,
                params={
                    "q": company_name,
                    "sort": sort,
                    "t": time_filter,
                    "limit": limit,
                    "type": "link",
                },
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("Reddit-Suche fehlgeschlagen: %s", e)
            return []

        data = resp.json()
        posts = data.get("data", {}).get("children", [])

        for post in posts:
            p = post.get("data", {})
            title = p.get("title", "")
            subreddit = p.get("subreddit", "")
            author = p.get("author", "[deleted]")
            score = p.get("score", 0)
            num_comments = p.get("num_comments", 0)
            selftext = p.get("selftext", "")[:500]
            permalink = p.get("permalink", "")
            created_utc = p.get("created_utc", 0)

            url = f"https://www.reddit.com{permalink}" if permalink else ""
            ts = datetime.fromtimestamp(created_utc, tz=UTC) if created_utc else datetime.now(UTC)

            events.append(NormalizedEvent(
                source="reddit",
                event_type="social_mention",
                title=f"r/{subreddit}: {title}",
                description=selftext or title,
                url=url,
                timestamp=ts,
                raw_data={
                    "platform": "reddit",
                    "subreddit": subreddit,
                    "author": author,
                    "score": score,
                    "num_comments": num_comments,
                    "selftext": selftext,
                    "upvote_ratio": p.get("upvote_ratio", 0),
                },
            ))

    log.info("Reddit: %d Posts für '%s' gefunden", len(events), company_name)
    return events
