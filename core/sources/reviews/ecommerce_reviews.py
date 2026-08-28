"""E-Commerce-Bewertungen: eKomi und Trusted Shops (deutsche Siegel-Anbieter)."""

import logging
import re

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9",
}


async def fetch_ekomi_reviews(company_name: str, limit: int = 15) -> list[dict]:
    """Scraped eKomi-Bewertungen.

    eKomi ist ein deutsches Bewertungssiegel für Online-Shops und Dienstleister.
    """
    reviews: list[dict] = []

    # eKomi-Slug aus Firmennamen ableiten
    slug = re.sub(r"[^a-z0-9]+", "-", company_name.lower()).strip("-")

    async with httpx.AsyncClient(timeout=15.0, headers=HEADERS, follow_redirects=True) as client:
        # Direkt die Profilseite versuchen
        profile_url = f"https://www.ekomi.de/bewertungen-{slug}.html"

        try:
            resp = await client.get(profile_url)
            if resp.status_code == 404:
                # Fallback: Google-Suche über eKomi wäre zu aufwändig,
                # stattdessen alternative URL-Muster probieren
                profile_url = f"https://www.ekomi.de/bewertungen/{slug}/"
                resp = await client.get(profile_url)

            if resp.status_code != 200:
                log.info("eKomi: Kein Profil für '%s' gefunden", company_name)
                return []
        except httpx.HTTPError as e:
            log.warning("eKomi fehlgeschlagen: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Gesamtbewertung
        rating_el = soup.select_one(
            '[class*="rating-score"], [itemprop="ratingValue"], '
            '.score-value, [class*="overall-score"]'
        )
        count_el = soup.select_one('[itemprop="reviewCount"], [class*="review-count"]')

        avg_rating = None
        if rating_el:
            r_text = rating_el.get_text(strip=True).replace(",", ".")
            match = re.search(r"(\d+\.?\d*)", r_text)
            if match:
                avg_rating = float(match.group(1))

        review_count = None
        if count_el:
            match = re.search(r"(\d+)", count_el.get_text(strip=True).replace(".", ""))
            if match:
                review_count = int(match.group(1))

        if avg_rating or review_count:
            reviews.append({
                "platform": "ekomi",
                "type": "summary",
                "company": company_name,
                "avg_rating": avg_rating,
                "review_count": review_count,
                "text": f"eKomi: {avg_rating or '?'}/5 ({review_count or '?'} Bewertungen)",
                "url": profile_url,
            })

        # Einzelbewertungen
        review_cards = soup.select('[class*="review-item"], [itemprop="review"], .feedback-item')
        for card in review_cards[:limit]:
            text_el = card.select_one('[itemprop="reviewBody"], [class*="text"], p')
            r_el = card.select_one('[itemprop="ratingValue"], [class*="stars"]')
            date_el = card.select_one('[itemprop="datePublished"], time, [class*="date"]')

            text = text_el.get_text(strip=True) if text_el else ""
            if not text:
                continue

            card_rating = None
            if r_el:
                r_match = re.search(r"(\d+[,.]?\d*)", r_el.get_text(strip=True).replace(",", "."))
                if r_match:
                    card_rating = float(r_match.group(1))

            date_str = ""
            if date_el:
                date_str = date_el.get("datetime", date_el.get("content", "")) or date_el.get_text(strip=True)

            reviews.append({
                "platform": "ekomi",
                "type": "review",
                "company": company_name,
                "rating": card_rating,
                "title": "",
                "text": text[:500],
                "date": date_str[:10] if date_str else "",
                "url": profile_url,
            })

    log.info("eKomi: %d Einträge für '%s'", len(reviews), company_name)
    return reviews


async def fetch_trustedshops_reviews(company_name: str, limit: int = 15) -> list[dict]:
    """Scraped Trusted Shops Bewertungen.

    Trusted Shops ist das bekannteste deutsche E-Commerce-Gütesiegel.
    """
    reviews: list[dict] = []

    async with httpx.AsyncClient(timeout=15.0, headers=HEADERS, follow_redirects=True) as client:
        # Trusted Shops Suche
        try:
            resp = await client.get(
                "https://www.trustedshops.de/shops/",
                params={"q": company_name},
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("Trusted Shops Suche fehlgeschlagen: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Profil-Link finden
        profile_link = soup.select_one(
            'a[href*="/bewertung/"], a[href*="/evaluation/"], '
            '.shop-result a[href], [class*="shop-link"] a'
        )
        if not profile_link:
            log.info("Trusted Shops: Kein Profil für '%s' gefunden", company_name)
            return []

        profile_url = profile_link.get("href", "")
        if not profile_url.startswith("http"):
            profile_url = f"https://www.trustedshops.de{profile_url}"

        # Profilseite laden
        try:
            resp = await client.get(profile_url)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("Trusted Shops Profil fehlgeschlagen: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Gesamtbewertung
        rating_el = soup.select_one(
            '[class*="rating-value"], [itemprop="ratingValue"], '
            '[data-testid="rating"], .overall-mark'
        )
        count_el = soup.select_one('[itemprop="reviewCount"], [class*="count"]')

        avg_rating = None
        if rating_el:
            r_text = rating_el.get_text(strip=True).replace(",", ".")
            match = re.search(r"(\d+\.?\d*)", r_text)
            if match:
                avg_rating = float(match.group(1))

        review_count = None
        if count_el:
            match = re.search(r"(\d+)", count_el.get_text(strip=True).replace(".", ""))
            if match:
                review_count = int(match.group(1))

        if avg_rating or review_count:
            reviews.append({
                "platform": "trustedshops",
                "type": "summary",
                "company": company_name,
                "avg_rating": avg_rating,
                "review_count": review_count,
                "text": f"Trusted Shops: {avg_rating or '?'}/5 ({review_count or '?'} Bewertungen)",
                "url": profile_url,
            })

        # Einzelbewertungen
        review_cards = soup.select('[itemprop="review"], [class*="review-item"], .review-card')
        for card in review_cards[:limit]:
            text_el = card.select_one('[itemprop="reviewBody"], [class*="text"], p')
            r_el = card.select_one('[itemprop="ratingValue"]')
            date_el = card.select_one('[itemprop="datePublished"], time')

            text = text_el.get_text(strip=True) if text_el else ""
            if not text:
                continue

            card_rating = None
            if r_el:
                r_match = re.search(r"(\d+[,.]?\d*)", r_el.get_text(strip=True).replace(",", "."))
                if r_match:
                    card_rating = float(r_match.group(1))

            date_str = ""
            if date_el:
                date_str = date_el.get("datetime", date_el.get("content", "")) or date_el.get_text(strip=True)

            reviews.append({
                "platform": "trustedshops",
                "type": "review",
                "company": company_name,
                "rating": card_rating,
                "title": "",
                "text": text[:500],
                "date": date_str[:10] if date_str else "",
                "url": profile_url,
            })

    log.info("Trusted Shops: %d Einträge für '%s'", len(reviews), company_name)
    return reviews
