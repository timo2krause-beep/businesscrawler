"""Review Monitor: Sammelt Bewertungen von allen Plattformen und erstellt KI-Analyse.

Quellen: Google Reviews, Trustpilot, Kununu, Glassdoor, ProvenExpert, App Store, Play Store.
"""

import logging

from core.ai_service import ai_chat
from core.base_module import BaseModule, Report, ReportItem
from core.sources.reviews.appstore_reviews import fetch_appstore_reviews, fetch_playstore_reviews
from core.sources.reviews.ecommerce_reviews import fetch_ekomi_reviews, fetch_trustedshops_reviews
from core.sources.reviews.german_local_reviews import (
    fetch_11880_reviews,
    fetch_golocal_reviews,
    fetch_kennstdueinen_reviews,
)
from core.sources.reviews.glassdoor_reviews import fetch_glassdoor_reviews
from core.sources.reviews.google_reviews import fetch_google_reviews
from core.sources.reviews.jameda_reviews import fetch_jameda_reviews
from core.sources.reviews.kununu_reviews import fetch_kununu_reviews
from core.sources.reviews.provenexpert_reviews import fetch_provenexpert_reviews
from core.sources.reviews.tripadvisor_reviews import fetch_tripadvisor_reviews
from core.sources.reviews.trustpilot_reviews import fetch_trustpilot_reviews

log = logging.getLogger(__name__)

PLATFORM_LABELS = {
    "google": "Google Reviews",
    "trustpilot": "Trustpilot",
    "kununu": "Kununu",
    "glassdoor": "Glassdoor",
    "provenexpert": "ProvenExpert",
    "appstore": "Apple App Store",
    "playstore": "Google Play Store",
    "tripadvisor": "Tripadvisor",
    "jameda": "Jameda",
    "11880": "11880.com",
    "golocal": "GoLocal",
    "kennstdueinen": "KennstDuEinen",
    "ekomi": "eKomi",
    "trustedshops": "Trusted Shops",
}

REVIEW_ANALYSIS_PROMPT = """Du bist ein Reputations-Analyst. Analysiere die gesammelten Bewertungen eines Unternehmens
von verschiedenen Plattformen und erstelle einen kompakten Bericht auf Deutsch.

Struktur:

## Bewertungs-Übersicht: [Firma]

### Gesamtbild
2-3 Sätze: Wie steht das Unternehmen insgesamt da? Welche Plattform hat die besten/schlechtesten Bewertungen?

### Plattform-Vergleich
Tabelle oder Liste: Plattform | Bewertung | Anzahl | Tendenz

### Stärken (was Kunden/Mitarbeiter loben)
Top 3-5 wiederkehrende positive Themen aus den Bewertungen.

### Schwächen (was kritisiert wird)
Top 3-5 wiederkehrende negative Themen aus den Bewertungen.

### Handlungsempfehlungen
2-3 konkrete Empfehlungen basierend auf den Bewertungen.

Schreibe klar und geschäftsorientiert. Nutze Markdown-Formatierung."""


class ReviewMonitor(BaseModule):
    name = "review_monitor"
    description = "Bewertungs-Monitor: Sammelt Rezensionen von Google, Trustpilot, Kununu, Glassdoor, ProvenExpert und App Stores"

    # Alle verfügbaren Plattformen und ihre Fetch-Funktionen
    ALL_SOURCES = {
        "google": lambda name, **kw: fetch_google_reviews(name, **kw),
        "trustpilot": lambda name, **kw: fetch_trustpilot_reviews(name),
        "kununu": lambda name, **kw: fetch_kununu_reviews(name),
        "glassdoor": lambda name, **kw: fetch_glassdoor_reviews(name),
        "provenexpert": lambda name, **kw: fetch_provenexpert_reviews(name),
        "appstore": lambda name, **kw: fetch_appstore_reviews(name),
        "playstore": lambda name, **kw: fetch_playstore_reviews(name),
        "tripadvisor": lambda name, **kw: fetch_tripadvisor_reviews(name, location=kw.get("location", "")),
        "jameda": lambda name, **kw: fetch_jameda_reviews(name),
        "11880": lambda name, **kw: fetch_11880_reviews(name, location=kw.get("location", "")),
        "golocal": lambda name, **kw: fetch_golocal_reviews(name, location=kw.get("location", "")),
        "kennstdueinen": lambda name, **kw: fetch_kennstdueinen_reviews(name, location=kw.get("location", "")),
        "ekomi": lambda name, **kw: fetch_ekomi_reviews(name),
        "trustedshops": lambda name, **kw: fetch_trustedshops_reviews(name),
    }

    def __init__(self, company_name: str = "", platforms: list[str] | None = None, location: str = ""):
        self.company_name = company_name
        self.platforms = platforms  # None = alle, Liste = nur diese
        self.location = location

    async def _collect_reviews(self) -> list[dict]:
        """Sammelt Reviews von relevanten Plattformen. Jede darf fehlschlagen."""
        all_reviews = []

        active = self.platforms if self.platforms else list(self.ALL_SOURCES.keys())
        sources = []
        for name in active:
            if name not in self.ALL_SOURCES:
                continue
            sources.append((name, self.ALL_SOURCES[name](self.company_name, location=self.location)))

        for name, coro in sources:
            try:
                results = await coro
                all_reviews.extend(results)
                log.info("%s: %d Ergebnisse", name, len(results))
            except Exception as e:
                log.warning("%s fehlgeschlagen: %s", name, e)

        return all_reviews

    async def _generate_analysis(self, reviews: list[dict]) -> str:
        """Erstellt KI-Analyse über alle gesammelten Reviews."""
        if not reviews:
            return f"Keine Bewertungen für '{self.company_name}' gefunden."

        # Summaries und einzelne Reviews aufbereiten
        summaries = [r for r in reviews if r.get("type") == "summary"]
        individual = [r for r in reviews if r.get("type") == "review"]

        summary_lines = []
        for s in summaries:
            platform = PLATFORM_LABELS.get(s["platform"], s["platform"])
            summary_lines.append(f"- {platform}: {s.get('avg_rating', '?')}/5 ({s.get('review_count', '?')} Bewertungen)")

        review_lines = []
        for r in individual[:30]:
            platform = PLATFORM_LABELS.get(r["platform"], r["platform"])
            rating = f"{r['rating']}/5" if r.get("rating") else "?"
            review_lines.append(
                f"- [{platform}] ({rating}) {r.get('title', '')}: {r['text'][:200]}"
            )

        prompt = (
            f"Unternehmen: {self.company_name}\n\n"
            f"Bewertungs-Übersicht:\n" + "\n".join(summary_lines) + "\n\n"
            f"Einzelne Bewertungen ({len(individual)} gesamt, hier die Top {min(len(review_lines), 30)}):\n"
            + "\n".join(review_lines)
        )

        try:
            return await ai_chat(prompt, system=REVIEW_ANALYSIS_PROMPT, max_tokens=3000, task="review_monitor.analysis")
        except Exception as e:
            log.warning("Review-Analyse fehlgeschlagen: %s", e)
            return f"Analyse konnte nicht generiert werden: {e}"

    async def fetch_data(self) -> list[dict]:
        if not self.company_name:
            return [{
                "title": "Kein Unternehmen konfiguriert",
                "description": "Bitte gib einen Firmennamen in den Moduleinstellungen an.",
                "url": "",
                "category": "info",
            }]

        log.info("Sammle Bewertungen für: %s", self.company_name)
        reviews = await self._collect_reviews()

        if not reviews:
            return [{
                "title": f"Keine Bewertungen für '{self.company_name}'",
                "description": "Auf keiner der Plattformen wurden Bewertungen gefunden.",
                "url": "",
                "category": "info",
            }]

        # KI-Analyse generieren
        analysis = await self._generate_analysis(reviews)

        # Statistiken
        summaries = [r for r in reviews if r.get("type") == "summary"]
        individual = [r for r in reviews if r.get("type") == "review"]
        platforms_found = list({s["platform"] for s in summaries})

        results = []

        # KI-Analyse als Haupt-Item
        results.append({
            "title": f"Bewertungs-Analyse: {self.company_name}",
            "description": analysis,
            "url": "",
            "category": "important",
            "is_analysis": True,
            "stats": {
                "platforms": len(platforms_found),
                "total_reviews": len(individual),
                "platform_list": platforms_found,
            },
        })

        # Plattform-Summaries
        for s in summaries:
            platform = PLATFORM_LABELS.get(s["platform"], s["platform"])
            results.append({
                "title": f"{platform}: {s.get('avg_rating', '?')}/5",
                "description": s["text"],
                "url": s.get("url", ""),
                "category": "info",
                "platform": s["platform"],
                "avg_rating": s.get("avg_rating"),
                "review_count": s.get("review_count"),
            })

        # Top einzelne Reviews (beste und schlechteste)
        rated = [r for r in individual if r.get("rating") is not None]
        rated.sort(key=lambda x: float(str(x.get("rating", 3)).replace(",", ".")))

        # Schlechteste zuerst
        for r in rated[:3]:
            platform = PLATFORM_LABELS.get(r["platform"], r["platform"])
            results.append({
                "title": f"[Kritisch] {platform}: {r.get('title', r['text'][:50])}",
                "description": r["text"],
                "url": r.get("url", ""),
                "category": "critical" if float(str(r.get("rating", 3)).replace(",", ".")) <= 2 else "info",
                "platform": r["platform"],
                "rating": r.get("rating"),
            })

        # Beste
        for r in rated[-3:]:
            platform = PLATFORM_LABELS.get(r["platform"], r["platform"])
            results.append({
                "title": f"[Positiv] {platform}: {r.get('title', r['text'][:50])}",
                "description": r["text"],
                "url": r.get("url", ""),
                "category": "info",
                "platform": r["platform"],
                "rating": r.get("rating"),
            })

        return results

    def process_data(self, raw_data: list[dict]) -> list[ReportItem]:
        items = []
        for entry in raw_data:
            cat = entry.get("category", "info")
            items.append(ReportItem(
                title=entry["title"],
                category=cat,
                summary=entry["description"] if entry.get("is_analysis") else entry["description"][:2000],
                source_url=entry.get("url", ""),
                metadata={
                    "platform": entry.get("platform"),
                    "avg_rating": entry.get("avg_rating"),
                    "review_count": entry.get("review_count"),
                    "rating": entry.get("rating"),
                    "stats": entry.get("stats"),
                    "is_analysis": entry.get("is_analysis", False),
                },
            ))
        return items

    def generate_report(self, items: list[ReportItem]) -> Report:
        return Report(
            module_name=self.name,
            title=f"Bewertungs-Monitor – {self.company_name or 'Nicht konfiguriert'}",
            items=items,
        )
