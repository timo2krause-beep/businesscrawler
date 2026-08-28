"""Deutsche lokale Bewertungsportale: 11880, GoLocal, KennstDuEinen."""

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


async def fetch_11880_reviews(company_name: str, location: str = "", limit: int = 10) -> list[dict]:
    """Scraped Bewertungen von 11880.com (Deutsches Branchenbuch)."""
    reviews: list[dict] = []
    search_query = company_name
    location_param = location or ""

    async with httpx.AsyncClient(timeout=15.0, headers=HEADERS, follow_redirects=True) as client:
        try:
            resp = await client.get(
                "https://www.11880.com/suche",
                params={"q": search_query, "loc": location_param},
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("11880-Suche fehlgeschlagen: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Erstes Ergebnis mit Bewertungen finden
        result = soup.select_one('a[href*="/branchenbuch/"], .result-item a, [data-testid="result"] a')
        if not result:
            log.info("11880: Kein Ergebnis für '%s'", company_name)
            return []

        profile_url = result.get("href", "")
        if not profile_url.startswith("http"):
            profile_url = f"https://www.11880.com{profile_url}"

        try:
            resp = await client.get(profile_url)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("11880-Profil fehlgeschlagen: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Rating extrahieren
        rating_el = soup.select_one('[class*="rating"], [itemprop="ratingValue"]')
        count_el = soup.select_one('[itemprop="reviewCount"], [class*="review-count"]')

        avg_rating = None
        if rating_el:
            r_text = rating_el.get_text(strip=True).replace(",", ".")
            match = re.search(r"(\d+\.?\d*)", r_text)
            if match:
                avg_rating = float(match.group(1))

        review_count = None
        if count_el:
            match = re.search(r"(\d+)", count_el.get_text(strip=True))
            if match:
                review_count = int(match.group(1))

        if avg_rating or review_count:
            reviews.append({
                "platform": "11880",
                "type": "summary",
                "company": company_name,
                "avg_rating": avg_rating,
                "review_count": review_count,
                "text": f"11880: {avg_rating or '?'}/5 ({review_count or '?'} Bewertungen)",
                "url": profile_url,
            })

        # Einzelbewertungen
        review_cards = soup.select('[class*="review"], [itemprop="review"]')
        for card in review_cards[:limit]:
            text_el = card.select_one('[itemprop="reviewBody"], [class*="text"], p')
            r_el = card.select_one('[itemprop="ratingValue"]')

            text = text_el.get_text(strip=True) if text_el else ""
            if not text:
                continue

            card_rating = None
            if r_el:
                r_match = re.search(r"(\d+\.?\d*)", r_el.get_text(strip=True).replace(",", "."))
                if r_match:
                    card_rating = float(r_match.group(1))

            reviews.append({
                "platform": "11880",
                "type": "review",
                "company": company_name,
                "rating": card_rating,
                "title": "",
                "text": text[:500],
                "date": "",
                "url": profile_url,
            })

    log.info("11880: %d Einträge für '%s'", len(reviews), company_name)
    return reviews


async def fetch_golocal_reviews(company_name: str, location: str = "", limit: int = 10) -> list[dict]:
    """Scraped Bewertungen von GoLocal.de."""
    reviews: list[dict] = []
    search_query = f"{company_name} {location}".strip() if location else company_name

    async with httpx.AsyncClient(timeout=15.0, headers=HEADERS, follow_redirects=True) as client:
        try:
            resp = await client.get(
                "https://www.golocal.de/suche/",
                params={"q": search_query},
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("GoLocal-Suche fehlgeschlagen: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        profile_link = soup.select_one('a[href*="/bewertung/"], .search-result a[href]')
        if not profile_link:
            log.info("GoLocal: Kein Ergebnis für '%s'", company_name)
            return []

        profile_url = profile_link.get("href", "")
        if not profile_url.startswith("http"):
            profile_url = f"https://www.golocal.de{profile_url}"

        try:
            resp = await client.get(profile_url)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("GoLocal-Profil fehlgeschlagen: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        rating_el = soup.select_one('[class*="rating-value"], [itemprop="ratingValue"]')
        count_el = soup.select_one('[itemprop="reviewCount"], [class*="count"]')

        avg_rating = None
        if rating_el:
            match = re.search(r"(\d+[,.]?\d*)", rating_el.get_text(strip=True))
            if match:
                avg_rating = float(match.group(1).replace(",", "."))

        review_count = None
        if count_el:
            match = re.search(r"(\d+)", count_el.get_text(strip=True))
            if match:
                review_count = int(match.group(1))

        if avg_rating or review_count:
            reviews.append({
                "platform": "golocal",
                "type": "summary",
                "company": company_name,
                "avg_rating": avg_rating,
                "review_count": review_count,
                "text": f"GoLocal: {avg_rating or '?'}/5 ({review_count or '?'} Bewertungen)",
                "url": profile_url,
            })

        review_cards = soup.select('[class*="review"], [itemprop="review"]')
        for card in review_cards[:limit]:
            text_el = card.select_one('[itemprop="reviewBody"], [class*="text"], p')
            text = text_el.get_text(strip=True) if text_el else ""
            if not text:
                continue

            reviews.append({
                "platform": "golocal",
                "type": "review",
                "company": company_name,
                "rating": None,
                "title": "",
                "text": text[:500],
                "date": "",
                "url": profile_url,
            })

    log.info("GoLocal: %d Einträge für '%s'", len(reviews), company_name)
    return reviews


async def fetch_kennstdueinen_reviews(company_name: str, location: str = "", limit: int = 10) -> list[dict]:
    """Scraped Bewertungen von KennstDuEinen.de."""
    reviews: list[dict] = []
    search_query = f"{company_name} {location}".strip() if location else company_name

    async with httpx.AsyncClient(timeout=15.0, headers=HEADERS, follow_redirects=True) as client:
        try:
            resp = await client.get(
                "https://www.kennstdueinen.de/suche",
                params={"q": search_query},
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("KennstDuEinen-Suche fehlgeschlagen: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        profile_link = soup.select_one('a[href*="/bewertung/"], .result a[href]')
        if not profile_link:
            log.info("KennstDuEinen: Kein Ergebnis für '%s'", company_name)
            return []

        profile_url = profile_link.get("href", "")
        if not profile_url.startswith("http"):
            profile_url = f"https://www.kennstdueinen.de{profile_url}"

        try:
            resp = await client.get(profile_url)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("KennstDuEinen-Profil fehlgeschlagen: %s", e)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        rating_el = soup.select_one('[itemprop="ratingValue"], [class*="rating"]')
        count_el = soup.select_one('[itemprop="reviewCount"]')

        avg_rating = None
        if rating_el:
            match = re.search(r"(\d+[,.]?\d*)", rating_el.get_text(strip=True))
            if match:
                avg_rating = float(match.group(1).replace(",", "."))

        review_count = None
        if count_el:
            match = re.search(r"(\d+)", count_el.get_text(strip=True))
            if match:
                review_count = int(match.group(1))

        if avg_rating or review_count:
            reviews.append({
                "platform": "kennstdueinen",
                "type": "summary",
                "company": company_name,
                "avg_rating": avg_rating,
                "review_count": review_count,
                "text": f"KennstDuEinen: {avg_rating or '?'}/5 ({review_count or '?'} Bewertungen)",
                "url": profile_url,
            })

        review_cards = soup.select('[itemprop="review"], [class*="review-item"]')
        for card in review_cards[:limit]:
            text_el = card.select_one('[itemprop="reviewBody"], p')
            text = text_el.get_text(strip=True) if text_el else ""
            if not text:
                continue

            reviews.append({
                "platform": "kennstdueinen",
                "type": "review",
                "company": company_name,
                "rating": None,
                "title": "",
                "text": text[:500],
                "date": "",
                "url": profile_url,
            })

    log.info("KennstDuEinen: %d Einträge für '%s'", len(reviews), company_name)
    return reviews
