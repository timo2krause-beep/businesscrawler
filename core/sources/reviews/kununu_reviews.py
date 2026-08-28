"""Kununu Reviews: Scraped Arbeitgeber-Bewertungen."""

import logging
import re

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

KUNUNU_SEARCH = "https://www.kununu.com/de/search"


async def fetch_kununu_reviews(company_name: str, limit: int = 20) -> list[dict]:
    """Scraped Kununu-Arbeitgeberbewertungen."""
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
        # 1. Suche
        try:
            resp = await client.get(KUNUNU_SEARCH, params={"q": company_name})
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("Kununu-Suche fehlgeschlagen: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Erstes Unternehmensprofil finden
        profile_link = soup.select_one('a[href*="/de/"][class*="company"]')
        if not profile_link:
            # Fallback: beliebiger Link der auf ein Profil zeigt
            profile_link = soup.find("a", href=re.compile(r"/de/[^/]+$"))

        if not profile_link:
            log.info("Kununu: Kein Profil für '%s' gefunden", company_name)
            return []

        profile_path = profile_link.get("href", "")
        if not profile_path.startswith("http"):
            profile_path = f"https://www.kununu.com{profile_path}"

        # 2. Profilseite laden
        try:
            resp = await client.get(profile_path)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("Kununu-Profil fehlgeschlagen: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Gesamtbewertung
        score_el = soup.select_one('[class*="score"], [data-test="score"]')
        count_el = soup.find(string=re.compile(r'[\d.]+ Bewertungen'))

        avg_rating = score_el.get_text(strip=True) if score_el else None
        review_count = None
        if count_el:
            count_match = re.search(r'([\d.]+)', str(count_el))
            review_count = count_match.group(1) if count_match else None

        reviews.append({
            "platform": "kununu",
            "type": "summary",
            "company": company_name,
            "avg_rating": avg_rating,
            "review_count": review_count,
            "text": f"Kununu: {avg_rating or '?'}/5 ({review_count or '?'} Bewertungen)",
            "url": profile_path,
        })

        # 3. Reviews-Seite laden
        reviews_url = profile_path.rstrip("/") + "/kommentare"
        try:
            resp = await client.get(reviews_url)
            resp.raise_for_status()
        except httpx.HTTPError:
            return reviews

        soup = BeautifulSoup(resp.text, "html.parser")

        # Einzelne Reviews
        review_cards = soup.select('[class*="review-card"], article[class*="review"]')
        if not review_cards:
            review_cards = soup.select('[data-test*="review"]')

        for card in review_cards[:limit]:
            title_el = card.select_one('h3, [class*="title"]')
            text_el = card.select_one('[class*="description"], [class*="text"], p')
            score_el = card.select_one('[class*="score"], [class*="rating"]')

            title = title_el.get_text(strip=True) if title_el else ""
            text = text_el.get_text(strip=True) if text_el else ""
            rating = None
            if score_el:
                rating_match = re.search(r'(\d[.,]\d)', score_el.get_text())
                rating = rating_match.group(1) if rating_match else None

            if title or text:
                reviews.append({
                    "platform": "kununu",
                    "type": "review",
                    "company": company_name,
                    "rating": rating,
                    "title": title,
                    "text": (text or title)[:500],
                    "url": reviews_url,
                })

    log.info("Kununu: %d Einträge für '%s'", len(reviews), company_name)
    return reviews
