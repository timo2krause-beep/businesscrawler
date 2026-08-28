"""Trustpilot Reviews: Consumer API + Scraping Fallback."""

import logging
import re

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

# Trustpilot Business Units API (öffentlich, keine Auth nötig)
TP_API_BASE = "https://www.trustpilot.com/api/consumersitejson/v1"
TRUSTPILOT_SEARCH = "https://www.trustpilot.com/search"


async def fetch_trustpilot_reviews(company_name: str, limit: int = 20) -> list[dict]:
    """Holt Trustpilot-Bewertungen via Consumer API, Scraping als Fallback.

    1. Sucht Business Unit via Search-Seite
    2. Nutzt Consumer-API für Reviews (stabiler als DOM-Scraping)
    3. Fallback auf Scraping wenn API-Endpunkt sich ändert
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
        # 1. Business Unit finden via Search
        business_unit_id = None
        profile_path = ""

        try:
            resp = await client.get(TRUSTPILOT_SEARCH, params={"query": company_name})
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            result_link = soup.select_one('a[href*="/review/"]')
            if not result_link:
                log.info("Trustpilot: Kein Profil für '%s' gefunden", company_name)
                return []

            profile_path = result_link.get("href", "")
            if not profile_path.startswith("http"):
                profile_path = f"https://www.trustpilot.com{profile_path}"

            # Business Unit ID aus Seiten-Daten extrahieren
            resp = await client.get(profile_path)
            resp.raise_for_status()
            page_text = resp.text

            # ID aus JSON-LD oder __NEXT_DATA__ extrahieren
            id_match = re.search(r'"businessUnitId"\s*:\s*"([a-f0-9]+)"', page_text)
            if id_match:
                business_unit_id = id_match.group(1)

        except httpx.HTTPError as e:
            log.warning("Trustpilot-Suche fehlgeschlagen: %s", e)
            return []

        # 2. Consumer API versuchen
        if business_unit_id:
            try:
                api_reviews = await _fetch_via_api(client, business_unit_id, company_name, profile_path, limit)
                if api_reviews:
                    log.info("Trustpilot (API): %d Einträge für '%s'", len(api_reviews), company_name)
                    return api_reviews
            except Exception as e:
                log.debug("Trustpilot Consumer API fehlgeschlagen, nutze Scraping: %s", e)

        # 3. Fallback: Scraping
        soup = BeautifulSoup(page_text, "html.parser")
        reviews = _scrape_reviews(soup, company_name, profile_path, limit)

    log.info("Trustpilot (Scraping): %d Einträge für '%s'", len(reviews), company_name)
    return reviews


async def _fetch_via_api(
    client: httpx.AsyncClient,
    business_unit_id: str,
    company_name: str,
    profile_url: str,
    limit: int,
) -> list[dict]:
    """Holt Reviews über die Trustpilot Consumer JSON API."""
    reviews: list[dict] = []

    # Business Unit Info (Rating + Count)
    resp = await client.get(f"{TP_API_BASE}/businessunits/{business_unit_id}")
    resp.raise_for_status()
    bu_data = resp.json()

    avg_rating = bu_data.get("score", {}).get("trustScore")
    review_count = bu_data.get("numberOfReviews")

    reviews.append({
        "platform": "trustpilot",
        "type": "summary",
        "company": company_name,
        "avg_rating": avg_rating,
        "review_count": review_count,
        "text": f"Trustpilot: {avg_rating or '?'}/5 ({review_count or '?'} Bewertungen)",
        "url": profile_url,
    })

    # Einzelne Reviews
    resp = await client.get(
        f"{TP_API_BASE}/businessunits/{business_unit_id}/reviews",
        params={"perPage": min(limit, 20), "page": 1},
    )
    resp.raise_for_status()
    review_data = resp.json().get("reviews", [])

    for r in review_data[:limit]:
        rating = r.get("rating")
        title = r.get("title", "")
        text = r.get("text", "")
        created = r.get("createdAt", "")

        if title or text:
            reviews.append({
                "platform": "trustpilot",
                "type": "review",
                "company": company_name,
                "rating": rating,
                "title": title,
                "text": (text or title)[:500],
                "date": created[:10] if created else "",
                "url": profile_url,
            })

    return reviews


def _scrape_reviews(soup: BeautifulSoup, company_name: str, profile_url: str, limit: int) -> list[dict]:
    """Fallback: DOM Scraping wenn API nicht verfügbar."""
    reviews: list[dict] = []

    # Gesamtbewertung
    rating_el = soup.select_one('[data-rating-typography="true"]')
    count_el = soup.select_one('span[class*="numberOfReviews"]')
    if not count_el:
        count_el = soup.find(string=re.compile(r'[\d,.]+ (Bewertungen|reviews)', re.IGNORECASE))

    avg_rating = rating_el.get_text(strip=True) if rating_el else None
    review_count = None
    if count_el:
        count_text = count_el if isinstance(count_el, str) else count_el.get_text(strip=True)
        count_match = re.search(r'([\d,.]+)', count_text)
        review_count = count_match.group(1) if count_match else None

    reviews.append({
        "platform": "trustpilot",
        "type": "summary",
        "company": company_name,
        "avg_rating": avg_rating,
        "review_count": review_count,
        "text": f"Trustpilot: {avg_rating or '?'}/5 ({review_count or '?'} Bewertungen)",
        "url": profile_url,
    })

    # Einzelne Reviews
    review_cards = soup.select('[data-service-review-card-paper="true"]')
    if not review_cards:
        review_cards = soup.select('article')

    for card in review_cards[:limit]:
        title_el = card.select_one('h2, [data-service-review-title-typography]')
        text_el = card.select_one('p[data-service-review-text-typography], .review-content__text')
        rating_el = card.select_one('[data-service-review-rating]')
        date_el = card.select_one('time')

        title = title_el.get_text(strip=True) if title_el else ""
        text = text_el.get_text(strip=True) if text_el else ""
        rating = rating_el.get("data-service-review-rating") if rating_el else None
        date_str = date_el.get("datetime", "") if date_el else ""

        if title or text:
            reviews.append({
                "platform": "trustpilot",
                "type": "review",
                "company": company_name,
                "rating": int(rating) if rating and rating.isdigit() else None,
                "title": title,
                "text": (text or title)[:500],
                "date": date_str[:10] if date_str else "",
                "url": profile_url,
            })

    return reviews
