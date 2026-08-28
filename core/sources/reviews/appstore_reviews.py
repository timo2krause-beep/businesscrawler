"""App Store Reviews: Apple App Store (RSS) und Google Play Store (Scraping)."""

import json
import logging
import re
import xml.etree.ElementTree as ET

import httpx

log = logging.getLogger(__name__)


async def fetch_appstore_reviews(app_name: str, limit: int = 20) -> list[dict]:
    """Sucht und scraped Apple App Store Reviews via RSS + iTunes Search API."""
    reviews = []

    async with httpx.AsyncClient(
        timeout=15.0,
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=True,
    ) as client:
        # 1. App-ID über iTunes Search API finden
        try:
            resp = await client.get(
                "https://itunes.apple.com/search",
                params={"term": app_name, "entity": "software", "country": "de", "limit": 1},
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            log.warning("iTunes-Suche fehlgeschlagen: %s", e)
            return []

        if not results:
            log.info("App Store: Keine App für '%s' gefunden", app_name)
            return []

        app = results[0]
        app_id = app.get("trackId")
        app_title = app.get("trackName", app_name)
        avg_rating = app.get("averageUserRating")
        rating_count = app.get("userRatingCount")

        reviews.append({
            "platform": "appstore",
            "type": "summary",
            "company": app_name,
            "app_name": app_title,
            "avg_rating": round(avg_rating, 1) if avg_rating else None,
            "review_count": rating_count,
            "text": f"App Store ({app_title}): {round(avg_rating, 1) if avg_rating else '?'}/5 ({rating_count or '?'} Bewertungen)",
            "url": app.get("trackViewUrl", ""),
        })

        # 2. Reviews via RSS Feed
        if app_id:
            rss_url = f"https://itunes.apple.com/de/rss/customerreviews/id={app_id}/sortBy=mostRecent/xml"
            try:
                resp = await client.get(rss_url)
                resp.raise_for_status()

                # Namespace handling
                ns = {"atom": "http://www.w3.org/2005/Atom", "im": "http://itunes.apple.com/rss"}
                root = ET.fromstring(resp.text)

                entries = root.findall("atom:entry", ns)
                for entry in entries[:limit]:
                    title = entry.findtext("atom:title", "", ns)
                    content = entry.findtext("atom:content", "", ns)
                    rating = entry.findtext("im:rating", "", ns)
                    author = entry.findtext("atom:author/atom:name", "", ns)
                    updated = entry.findtext("atom:updated", "", ns)

                    if title == app_title:
                        continue  # Skip the app entry itself

                    reviews.append({
                        "platform": "appstore",
                        "type": "review",
                        "company": app_name,
                        "rating": int(rating) if rating and rating.isdigit() else None,
                        "title": title,
                        "text": (content or title)[:500],
                        "author": author,
                        "date": updated[:10] if updated else "",
                        "url": app.get("trackViewUrl", ""),
                    })
            except (httpx.HTTPError, ET.ParseError) as e:
                log.warning("App Store RSS fehlgeschlagen: %s", e)

    log.info("App Store: %d Einträge für '%s'", len(reviews), app_name)
    return reviews


async def fetch_playstore_reviews(app_name: str, limit: int = 15) -> list[dict]:
    """Sucht und scraped Google Play Store Reviews."""
    reviews = []

    async with httpx.AsyncClient(
        timeout=15.0,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "de-DE,de;q=0.9",
        },
        follow_redirects=True,
    ) as client:
        # Suche im Play Store
        try:
            resp = await client.get(
                "https://play.google.com/store/search",
                params={"q": app_name, "c": "apps", "hl": "de"},
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("Play Store Suche fehlgeschlagen: %s", e)
            return []

        # App-Link finden
        app_match = re.search(r'/store/apps/details\?id=([^"&]+)', resp.text)
        if not app_match:
            log.info("Play Store: Keine App für '%s' gefunden", app_name)
            return []

        app_id = app_match.group(1)
        app_url = f"https://play.google.com/store/apps/details?id={app_id}&hl=de"

        # App-Seite laden
        try:
            resp = await client.get(app_url)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("Play Store App-Seite fehlgeschlagen: %s", e)
            return []

        # Rating extrahieren
        rating_match = re.search(r'(\d\.\d)\s*star', resp.text, re.IGNORECASE)
        if not rating_match:
            rating_match = re.search(r'"(\d\.\d)"', resp.text)

        avg_rating = float(rating_match.group(1)) if rating_match else None

        reviews.append({
            "platform": "playstore",
            "type": "summary",
            "company": app_name,
            "avg_rating": avg_rating,
            "text": f"Google Play ({app_name}): {avg_rating or '?'}/5",
            "url": app_url,
        })

    log.info("Play Store: %d Einträge für '%s'", len(reviews), app_name)
    return reviews
