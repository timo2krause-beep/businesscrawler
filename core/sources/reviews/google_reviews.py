"""Google Reviews via Places API (New)."""

import logging

import httpx

from config.settings import settings

log = logging.getLogger(__name__)

PLACES_BASE = "https://places.googleapis.com/v1"


async def fetch_google_reviews(company_name: str, limit: int = 10, location: str = "") -> list[dict]:
    """Holt Google Reviews über die offizielle Places API.

    1. Text Search → findet den Place (mit optionalem Location Bias)
    2. Place Details → holt Reviews
    """
    api_key = settings.google_places_api_key
    if not api_key:
        log.warning("Google Places API Key nicht konfiguriert – überspringe Google Reviews")
        return []

    reviews: list[dict] = []

    # Suchtext mit Standort anreichern für bessere lokale Treffer
    search_query = f"{company_name} {location}".strip() if location else company_name

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1) Text Search – Place finden
        try:
            search_body: dict = {"textQuery": search_query}
            # Sprachpräferenz Deutsch für bessere lokale Ergebnisse
            if location:
                search_body["languageCode"] = "de"

            search_resp = await client.post(
                f"{PLACES_BASE}/places:searchText",
                json=search_body,
                headers={
                    "X-Goog-Api-Key": api_key,
                    "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.googleMapsUri",
                },
            )
            search_resp.raise_for_status()
            places = search_resp.json().get("places", [])
        except httpx.HTTPError as e:
            log.warning("Google Places Text Search fehlgeschlagen: %s", e)
            return []

        if not places:
            log.info("Google Places: Kein Ergebnis für '%s'", company_name)
            return []

        place = places[0]
        place_id = place["id"]
        display_name = place.get("displayName", {}).get("text", company_name)
        avg_rating = place.get("rating")
        review_count = place.get("userRatingCount")
        maps_url = place.get("googleMapsUri", "")

        # Summary
        if avg_rating or review_count:
            reviews.append({
                "platform": "google",
                "type": "summary",
                "company": display_name,
                "avg_rating": avg_rating,
                "review_count": review_count,
                "text": f"Google-Bewertung: {avg_rating or '?'} Sterne ({review_count or '?'} Bewertungen)",
                "url": maps_url,
            })

        # 2) Place Details – Reviews holen
        try:
            detail_resp = await client.get(
                f"{PLACES_BASE}/places/{place_id}",
                headers={
                    "X-Goog-Api-Key": api_key,
                    "X-Goog-FieldMask": "reviews",
                },
            )
            detail_resp.raise_for_status()
            place_reviews = detail_resp.json().get("reviews", [])
        except httpx.HTTPError as e:
            log.warning("Google Places Details fehlgeschlagen: %s", e)
            return reviews  # Summary trotzdem zurückgeben

        for r in place_reviews[:limit]:
            author = r.get("authorAttribution", {}).get("displayName", "Anonym")
            rating = r.get("rating", 0)
            text = r.get("text", {}).get("text", "")
            publish_time = r.get("publishTime", "")
            relative_time = r.get("relativePublishTimeDescription", "")

            reviews.append({
                "platform": "google",
                "type": "review",
                "company": display_name,
                "author": author,
                "rating": rating,
                "text": text[:500],
                "date": relative_time or publish_time,
                "url": maps_url,
            })

    log.info("Google Reviews (Places API): %d Einträge für '%s'", len(reviews), company_name)
    return reviews
