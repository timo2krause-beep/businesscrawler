"""Glassdoor Reviews: Scraped Arbeitgeber-Bewertungen."""

import logging
import re

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)


async def fetch_glassdoor_reviews(company_name: str, limit: int = 15) -> list[dict]:
    """Scraped Glassdoor-Arbeitgeberbewertungen."""
    reviews = []

    async with httpx.AsyncClient(
        timeout=15.0,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        },
        follow_redirects=True,
    ) as client:
        # Glassdoor-Suche
        try:
            resp = await client.get(
                "https://www.glassdoor.com/Search/results.htm",
                params={"keyword": company_name, "typedKeyword": company_name},
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("Glassdoor-Suche fehlgeschlagen: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Firmen-Link finden
        company_link = soup.select_one('a[href*="/Reviews/"]')
        if not company_link:
            log.info("Glassdoor: Kein Profil für '%s' gefunden", company_name)
            return []

        profile_path = company_link.get("href", "")
        if not profile_path.startswith("http"):
            profile_path = f"https://www.glassdoor.com{profile_path}"

        # Profilseite laden
        try:
            resp = await client.get(profile_path)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("Glassdoor-Profil fehlgeschlagen: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Gesamtbewertung
        rating_el = soup.select_one('[class*="ratingNum"], [data-test="rating-num"]')
        count_el = soup.find(string=re.compile(r'[\d,.]+ (Reviews|Bewertungen)', re.IGNORECASE))

        avg_rating = rating_el.get_text(strip=True) if rating_el else None
        review_count = None
        if count_el:
            count_match = re.search(r'([\d,.]+)', str(count_el))
            review_count = count_match.group(1) if count_match else None

        reviews.append({
            "platform": "glassdoor",
            "type": "summary",
            "company": company_name,
            "avg_rating": avg_rating,
            "review_count": review_count,
            "text": f"Glassdoor: {avg_rating or '?'}/5 ({review_count or '?'} Bewertungen)",
            "url": profile_path,
        })

        # Einzelne Reviews
        review_cards = soup.select('[class*="empReview"], [id*="empReview"]')

        for card in review_cards[:limit]:
            title_el = card.select_one('[class*="reviewLink"], h2 a')
            pros_el = card.select_one('[class*="pros"], [data-test="pros"]')
            cons_el = card.select_one('[class*="cons"], [data-test="cons"]')
            rating_el = card.select_one('[class*="ratingNumber"]')
            date_el = card.select_one('[class*="date"], time')

            title = title_el.get_text(strip=True) if title_el else ""
            pros = pros_el.get_text(strip=True) if pros_el else ""
            cons = cons_el.get_text(strip=True) if cons_el else ""
            rating = rating_el.get_text(strip=True) if rating_el else None
            date_str = date_el.get_text(strip=True) if date_el else ""

            text_parts = []
            if pros:
                text_parts.append(f"Pro: {pros}")
            if cons:
                text_parts.append(f"Contra: {cons}")
            text = " | ".join(text_parts) or title

            if text:
                reviews.append({
                    "platform": "glassdoor",
                    "type": "review",
                    "company": company_name,
                    "rating": rating,
                    "title": title,
                    "text": text[:500],
                    "date": date_str,
                    "url": profile_path,
                })

    log.info("Glassdoor: %d Einträge für '%s'", len(reviews), company_name)
    return reviews
