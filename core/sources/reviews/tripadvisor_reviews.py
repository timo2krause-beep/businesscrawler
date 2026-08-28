"""Tripadvisor Reviews: Gastro/Hotel-Bewertungen."""

import logging
import re

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

TRIPADVISOR_SEARCH = "https://www.tripadvisor.de/Search"


async def fetch_tripadvisor_reviews(company_name: str, location: str = "", limit: int = 15) -> list[dict]:
    """Scraped Tripadvisor-Bewertungen.

    1. Sucht das Restaurant/Hotel
    2. Scraped die Bewertungen von der Profilseite
    """
    reviews: list[dict] = []
    search_query = f"{company_name} {location}".strip() if location else company_name

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
            resp = await client.get(TRIPADVISOR_SEARCH, params={"q": search_query})
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("Tripadvisor-Suche fehlgeschlagen: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Profil-Link finden (Restaurant, Hotel oder Attraktion)
        profile_link = soup.select_one(
            'a[href*="/Restaurant_Review-"], a[href*="/Hotel_Review-"], a[href*="/Attraction_Review-"]'
        )
        if not profile_link:
            log.info("Tripadvisor: Kein Profil für '%s' gefunden", company_name)
            return []

        profile_url = profile_link.get("href", "")
        if not profile_url.startswith("http"):
            profile_url = f"https://www.tripadvisor.de{profile_url}"

        # 2. Profilseite laden
        try:
            resp = await client.get(profile_url)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("Tripadvisor-Profil fehlgeschlagen: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Gesamtbewertung
        rating_el = soup.select_one(
            '[data-testid="rating-score"], .biGQs span[class*="rating"], '
            'span[class*="ZDEqb"], span[class*="average"]'
        )
        count_el = soup.select_one(
            '[data-testid="review-count"], a[href*="#REVIEWS"] span, '
            'span[class*="reviewCount"]'
        )

        avg_rating = None
        if rating_el:
            r_text = rating_el.get_text(strip=True).replace(",", ".")
            match = re.search(r"(\d+\.?\d*)", r_text)
            if match:
                avg_rating = float(match.group(1))

        review_count = None
        if count_el:
            c_text = count_el.get_text(strip=True).replace(".", "").replace(",", "")
            match = re.search(r"(\d+)", c_text)
            if match:
                review_count = int(match.group(1))

        reviews.append({
            "platform": "tripadvisor",
            "type": "summary",
            "company": company_name,
            "avg_rating": avg_rating,
            "review_count": review_count,
            "text": f"Tripadvisor: {avg_rating or '?'}/5 ({review_count or '?'} Bewertungen)",
            "url": profile_url,
        })

        # Einzelne Bewertungen
        review_cards = soup.select(
            '[data-testid="review-card"], div[class*="review-container"], '
            '.reviewSelector, [data-reviewid]'
        )

        for card in review_cards[:limit]:
            title_el = card.select_one(
                '[data-testid="review-title"], a[class*="title"], .noQuotes'
            )
            text_el = card.select_one(
                '[data-testid="review-text"], span[class*="QewHA"], .partial_entry, p'
            )
            bubble = card.select_one('[class*="bubble_rating"], svg[class*="rating"]')
            date_el = card.select_one('[class*="date"], time, span[class*="ratingDate"]')

            title = title_el.get_text(strip=True) if title_el else ""
            text = text_el.get_text(strip=True) if text_el else ""
            if not text and not title:
                continue

            card_rating = None
            if bubble:
                # class="bubble_50" = 5.0 Sterne, "bubble_40" = 4.0 etc.
                bubble_class = " ".join(bubble.get("class", []))
                r_match = re.search(r"bubble_(\d)0", bubble_class)
                if r_match:
                    card_rating = int(r_match.group(1))
                # Alternativ: aria-label
                aria = bubble.get("aria-label", "")
                a_match = re.search(r"(\d[,.]?\d?)", aria)
                if a_match and not card_rating:
                    card_rating = float(a_match.group(1).replace(",", "."))

            date_str = ""
            if date_el:
                date_str = date_el.get("datetime", "") or date_el.get_text(strip=True)

            reviews.append({
                "platform": "tripadvisor",
                "type": "review",
                "company": company_name,
                "rating": card_rating,
                "title": title,
                "text": (text or title)[:500],
                "date": date_str[:10] if date_str else "",
                "url": profile_url,
            })

    log.info("Tripadvisor: %d Einträge für '%s'", len(reviews), company_name)
    return reviews
