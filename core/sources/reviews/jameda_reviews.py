"""Jameda Reviews: Deutsche Arzt-Bewertungsplattform."""

import logging
import re

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

JAMEDA_SEARCH = "https://www.jameda.de/suche"


async def fetch_jameda_reviews(company_name: str, limit: int = 15) -> list[dict]:
    """Scraped Jameda-Bewertungen.

    1. Sucht den Arzt/die Praxis
    2. Scraped die Bewertungen von der Profilseite
    """
    reviews: list[dict] = []

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
            resp = await client.get(JAMEDA_SEARCH, params={"query": company_name})
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("Jameda-Suche fehlgeschlagen: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Erstes Profil-Link finden
        profile_link = soup.select_one('a[href*="/arzt/"], a[href*="/zahnarzt/"], a[href*="/praxis/"]')
        if not profile_link:
            # Alternativ: data-testid basiert
            profile_link = soup.select_one('[data-testid="search-result-link"], .search-result a[href]')

        if not profile_link:
            log.info("Jameda: Kein Profil für '%s' gefunden", company_name)
            return []

        profile_url = profile_link.get("href", "")
        if not profile_url.startswith("http"):
            profile_url = f"https://www.jameda.de{profile_url}"

        # 2. Profilseite laden
        try:
            resp = await client.get(profile_url)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("Jameda-Profil fehlgeschlagen: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Gesamtbewertung
        rating_el = soup.select_one('[class*="rating-score"], [data-testid="overall-rating"], .rating__score')
        count_el = soup.select_one('[class*="rating-count"], [data-testid="review-count"]')

        avg_rating = None
        if rating_el:
            rating_text = rating_el.get_text(strip=True).replace(",", ".")
            match = re.search(r"(\d+\.?\d*)", rating_text)
            if match:
                avg_rating = float(match.group(1))

        review_count = None
        if count_el:
            count_text = count_el.get_text(strip=True)
            match = re.search(r"(\d+)", count_text)
            if match:
                review_count = int(match.group(1))

        # Jameda nutzt Noten (1.0 = sehr gut, 6.0 = ungenügend) → auf 5-Sterne umrechnen
        avg_rating_stars = None
        if avg_rating:
            avg_rating_stars = round(max(1, min(5, 6 - avg_rating)), 1)

        reviews.append({
            "platform": "jameda",
            "type": "summary",
            "company": company_name,
            "avg_rating": avg_rating_stars,
            "review_count": review_count,
            "text": f"Jameda: Note {avg_rating or '?'} ({review_count or '?'} Bewertungen)",
            "url": profile_url,
        })

        # Einzelne Bewertungen
        review_cards = soup.select('[class*="review-card"], [data-testid="review-item"], .review-list__item')
        if not review_cards:
            review_cards = soup.select("article")

        for card in review_cards[:limit]:
            text_el = card.select_one('[class*="review-text"], [data-testid="review-text"], p')
            rating_el = card.select_one('[class*="rating"], [data-testid="rating"]')
            date_el = card.select_one("time, [class*='date']")

            text = text_el.get_text(strip=True) if text_el else ""
            if not text:
                continue

            card_rating = None
            if rating_el:
                r_text = rating_el.get_text(strip=True).replace(",", ".")
                r_match = re.search(r"(\d+\.?\d*)", r_text)
                if r_match:
                    note = float(r_match.group(1))
                    card_rating = round(max(1, min(5, 6 - note)), 1)

            date_str = ""
            if date_el:
                date_str = date_el.get("datetime", "") or date_el.get_text(strip=True)

            reviews.append({
                "platform": "jameda",
                "type": "review",
                "company": company_name,
                "rating": card_rating,
                "title": "",
                "text": text[:500],
                "date": date_str[:10] if date_str else "",
                "url": profile_url,
            })

    log.info("Jameda: %d Einträge für '%s'", len(reviews), company_name)
    return reviews
