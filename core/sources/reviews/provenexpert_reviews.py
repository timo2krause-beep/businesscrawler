"""ProvenExpert Reviews: Scraped Dienstleister-Bewertungen."""

import logging
import re

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)


async def fetch_provenexpert_reviews(company_name: str, limit: int = 15) -> list[dict]:
    """Scraped ProvenExpert-Bewertungen."""
    reviews = []

    # ProvenExpert-URLs sind slug-basiert, wir versuchen eine Suche
    slug = company_name.lower().replace(" ", "-").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")

    async with httpx.AsyncClient(
        timeout=15.0,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "de-DE,de;q=0.9",
        },
        follow_redirects=True,
    ) as client:
        # Versuche direkte URL
        profile_url = f"https://www.provenexpert.com/{slug}/"
        try:
            resp = await client.get(profile_url)
            if resp.status_code == 404:
                # Fallback: Google-Suche-artige Anfrage
                log.info("ProvenExpert: Kein Profil unter %s", profile_url)
                return []
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("ProvenExpert fehlgeschlagen: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Gesamtbewertung
        score_el = soup.select_one('[class*="rating-score"], .score-value')
        count_el = soup.find(string=re.compile(r'[\d.]+ Bewertungen'))

        avg_rating = score_el.get_text(strip=True) if score_el else None
        review_count = None
        if count_el:
            count_match = re.search(r'([\d.]+)', str(count_el))
            review_count = count_match.group(1) if count_match else None

        reviews.append({
            "platform": "provenexpert",
            "type": "summary",
            "company": company_name,
            "avg_rating": avg_rating,
            "review_count": review_count,
            "text": f"ProvenExpert: {avg_rating or '?'}/5 ({review_count or '?'} Bewertungen)",
            "url": profile_url,
        })

        # Einzelne Reviews
        review_els = soup.select('[class*="review-item"], [class*="testimonial"]')
        for el in review_els[:limit]:
            text_el = el.select_one('[class*="review-text"], p')
            rating_el = el.select_one('[class*="rating"], [class*="stars"]')
            date_el = el.select_one('[class*="date"], time')

            text = text_el.get_text(strip=True) if text_el else ""
            date_str = date_el.get_text(strip=True) if date_el else ""

            rating = None
            if rating_el:
                rating_match = re.search(r'(\d[.,]\d)', rating_el.get_text())
                rating = rating_match.group(1) if rating_match else None

            if text:
                reviews.append({
                    "platform": "provenexpert",
                    "type": "review",
                    "company": company_name,
                    "rating": rating,
                    "text": text[:500],
                    "date": date_str,
                    "url": profile_url,
                })

    log.info("ProvenExpert: %d Einträge für '%s'", len(reviews), company_name)
    return reviews
