"""KI-Wettbewerbsanalyse: Erkennt Wettbewerber per KI, erstellt Profile und überwacht deren Webseiten.

Wettbewerber-Profile werden in der DB gecacht und nur bei Bedarf aktualisiert:
- Erster Aufruf: KI identifiziert Wettbewerber → speichert in DB
- Folgeaufrufe: Nutzt gecachte Daten aus DB
- Refresh: Über trigger_refresh() oder needs_refresh Flag
"""

import logging

from core.ai_service import ai_chat, ai_json
from core.base_module import BaseModule, Report, ReportItem
from core.competitor_store import (
    format_competitor_card,
    load_competitors,
    needs_refresh,
    save_competitor,
)
from core.database import get_session
from core.event_store import load_content_hashes, load_content_texts, save_content_hash
from core.sources.web_scraper import ScrapingTarget, WebScraperSource

log = logging.getLogger(__name__)

COMPETITOR_SYSTEM_PROMPT = """Du bist ein erfahrener Marktanalyst und Wettbewerbsforscher.
Der Nutzer gibt dir Firmeninfos (Name, ggf. Standort und Größe). Identifiziere die 5 wichtigsten direkten Wettbewerber.

WICHTIG für die Wettbewerber-Auswahl:
- Vergleiche IMMER mit ähnlich großen Unternehmen im gleichen Marktsegment
- Bei lokalen Unternehmen (Restaurant, Handwerker, Arzt etc.): Suche Wettbewerber in der GLEICHEN Region/Stadt
- Bei Kleinunternehmen: Vergleiche mit anderen Kleinunternehmen, NICHT mit Konzernen
- Bei Konzernen/Ketten: Vergleiche mit anderen Konzernen im gleichen Markt
- Der Standort bestimmt den Suchradius: lokal → gleiche Stadt/Region, überregional → ganzes Land, international → global

Antworte ausschließlich als JSON-Array mit diesem Format:
[
  {
    "name": "Firmenname",
    "url": "https://www.example.com",
    "reason": "Warum direkter Wettbewerber (inkl. regionale Relevanz)",
    "founded": "Gründungsjahr",
    "hq": "Hauptsitz (Stadt, Land)",
    "size": "Unternehmensgröße (Mitarbeiter, z.B. '~500' oder '10.000+')",
    "revenue": "Geschätzter Jahresumsatz falls bekannt",
    "market_share": "Geschätzter Marktanteil oder Marktposition",
    "products": ["Hauptprodukt 1", "Hauptprodukt 2", "Hauptprodukt 3"],
    "strengths": ["Stärke 1", "Stärke 2"],
    "weaknesses": ["Schwäche 1", "Schwäche 2"],
    "target_customers": "Zielgruppe",
    "pricing_model": "Preismodell"
  }
]

Wichtig:
- Nur echte, erreichbare URLs (Hauptdomain)
- Alle Felder nach bestem Wissen ausfüllen
- Bei Unsicherheit ehrlich 'unbekannt' angeben
- Nur JSON ausgeben, kein anderer Text"""

PROFILE_SYSTEM_PROMPT = """Du bist ein Marktanalyst. Erstelle eine kompakte Wettbewerbsanalyse auf Deutsch.
Fasse die Informationen über den Wettbewerber und dessen Verhältnis zum analysierten Unternehmen zusammen.

Struktur:
1. **Unternehmensprofil**: Größe, Standort, Gründung
2. **Produkte & Positionierung**: Hauptprodukte, Zielgruppe, Preismodell
3. **Marktposition**: Marktanteil, Stärken, Schwächen
4. **Aktuelle Entwicklungen**: Bekannte News, Trends, strategische Richtung
5. **Bedrohungspotenzial**: Wie stark ist dieser Wettbewerber für das analysierte Unternehmen?

Halte es auf 8-12 Sätze. Schreibe klar und geschäftsorientiert."""

DIFF_SYSTEM_PROMPT = """Du bist ein Analyst für Wettbewerbsbeobachtung. Dir werden Änderungen auf einer Wettbewerber-Webseite gezeigt.
Formuliere eine klare, geschäftsrelevante Zusammenfassung der Änderungen auf Deutsch.
Fokussiere dich auf: Preisänderungen, neue Produkte/Features, strategische Änderungen, wichtige Ankündigungen.
Ignoriere rein kosmetische Änderungen (Layout, Tippfehler, Datumsänderungen).
Halte die Zusammenfassung auf 2-4 Sätze."""

RECOMMENDATIONS_SYSTEM_PROMPT = """Du bist ein Business-Berater für kleine und mittlere Unternehmen.
Du bekommst eine Wettbewerbsanalyse (Profile der Wettbewerber und ggf. aktuelle Änderungen bei ihnen).
Leite daraus 3-5 KONKRETE, SOFORT UMSETZBARE Handlungsempfehlungen für das analysierte Unternehmen ab.

Anforderungen an jede Empfehlung:
- Eine klare, direkt umsetzbare Handlung (kein "prüfe, ob..." oder "überlege dir..." – sondern eine echte Handlung)
- Eine kurze Begründung MIT Bezug auf einen konkreten Wettbewerber aus den Daten
- Priorität: "hoch", "mittel" oder "niedrig"
- Kategorie: "Preise", "Marketing", "Produkt" oder "Sonstiges"

Antworte ausschließlich als JSON-Array mit diesem Format:
[
  {
    "action": "Konkrete Handlung in 1-2 Sätzen",
    "reason": "Begründung mit Bezug auf einen bestimmten Wettbewerber",
    "priority": "hoch",
    "category": "Preise"
  }
]

Wichtig:
- Erfinde keine Wettbewerber-Fakten, die dir nicht gegeben wurden
- Bei zu wenig Datengrundlage lieber weniger, dafür fundierte Empfehlungen
- Nur JSON ausgeben, kein anderer Text"""

class KIWettbewerbMonitor(BaseModule):
    name = "ki_wettbewerb"
    description = "KI-gestützte Wettbewerbsanalyse: Erkennt Wettbewerber automatisch und überwacht deren Webseiten"

    def __init__(
        self,
        company_name: str = "",
        location: str = "",
        company_size: str = "",
        force_refresh: bool = False,
    ):
        self.company_name = company_name
        self.location = location
        self.company_size = company_size
        self.force_refresh = force_refresh
        self._competitors: list[dict] = []

    async def _identify_competitors_ai(self) -> list[dict]:
        """Fragt die KI nach Wettbewerbern mit detaillierten Profildaten."""
        log.info("KI identifiziert Wettbewerber für: %s (Standort: %s, Größe: %s)",
                 self.company_name, self.location or "-", self.company_size or "-")

        prompt = f"Firma: {self.company_name}"
        if self.location:
            prompt += f"\nStandort: {self.location}"
        if self.company_size:
            size_labels = {
                "solo": "Einzelunternehmen",
                "klein": "Kleinunternehmen (2-20 Mitarbeiter)",
                "mittel": "Mittelstand (20-250 Mitarbeiter)",
                "gross": "Großunternehmen (250+ Mitarbeiter)",
                "konzern": "Konzern / Kette",
            }
            prompt += f"\nUnternehmensgröße: {size_labels.get(self.company_size, self.company_size)}"
        prompt += "\n\nIdentifiziere die 5 wichtigsten direkten Wettbewerber."

        result = await ai_json(prompt, system=COMPETITOR_SYSTEM_PROMPT)
        if not isinstance(result, list):
            log.warning("KI hat kein Array zurückgegeben: %s", type(result))
            return []

        log.info("KI hat %d Wettbewerber identifiziert", len(result))
        return result

    async def _create_profile_ai(self, competitor: dict) -> str:
        """Erstellt ein ausformuliertes KI-Profil für einen Wettbewerber."""
        prompt = (
            f"Analysiertes Unternehmen: {self.company_name}\n\n"
            f"Wettbewerber: {competitor.get('name', '?')}\n"
            f"URL: {competitor.get('url', '')}\n"
            f"Begründung: {competitor.get('reason', '')}\n"
            f"Gründung: {competitor.get('founded', 'unbekannt')}\n"
            f"Hauptsitz: {competitor.get('hq', 'unbekannt')}\n"
            f"Größe: {competitor.get('size', 'unbekannt')}\n"
            f"Umsatz: {competitor.get('revenue', 'unbekannt')}\n"
            f"Marktanteil: {competitor.get('market_share', 'unbekannt')}\n"
            f"Produkte: {', '.join(competitor.get('products', []))}\n"
            f"Stärken: {', '.join(competitor.get('strengths', []))}\n"
            f"Schwächen: {', '.join(competitor.get('weaknesses', []))}\n"
            f"Zielkunden: {competitor.get('target_customers', 'unbekannt')}\n"
            f"Preismodell: {competitor.get('pricing_model', 'unbekannt')}\n"
        )
        try:
            return await ai_chat(prompt, system=PROFILE_SYSTEM_PROMPT)
        except Exception as e:
            log.warning("Profil-Erstellung fehlgeschlagen für %s: %s", competitor.get("name"), e)
            return ""

    async def _load_or_refresh_competitors(self) -> tuple[list[dict], list[str]]:
        """Lädt Wettbewerber aus DB-Cache oder holt sie neu per KI.

        Returns:
            (competitors, ai_profiles) — Liste der Wettbewerber-Dicts und zugehörige Profile.
        """
        with get_session() as db:
            refresh_needed = self.force_refresh or needs_refresh(db, self.company_name)

        if not refresh_needed:
            # Aus DB laden — Daten innerhalb der Session extrahieren
            log.info("Lade Wettbewerber aus Cache für: %s", self.company_name)
            with get_session() as db:
                cached = load_competitors(db, self.company_name)
                competitors = [row.competitor_data for row in cached]
                profiles = [row.ai_profile or "" for row in cached]
            log.info("%d Wettbewerber aus DB geladen", len(competitors))
            return competitors, profiles

        # Neu per KI identifizieren
        competitors = await self._identify_competitors_ai()
        if not competitors:
            return [], []

        # Profile per KI generieren
        profiles = []
        for comp in competitors:
            profile = await self._create_profile_ai(comp)
            profiles.append(profile)

        # In DB speichern
        with get_session() as db:
            for comp, profile in zip(competitors, profiles):
                save_competitor(db, self.company_name, comp, ai_profile=profile)
            db.commit()
        log.info("%d Wettbewerber in DB gespeichert", len(competitors))

        return competitors, profiles

    async def _summarize_change(self, target_name: str, url: str, diff: str) -> str:
        """Lässt die KI eine Webseitenänderung zusammenfassen."""
        prompt = (
            f"Webseite: {target_name} ({url})\n\n"
            f"Erkannte Änderungen:\n{diff}"
        )
        try:
            return await ai_chat(prompt, system=DIFF_SYSTEM_PROMPT)
        except Exception as e:
            log.warning("KI-Zusammenfassung fehlgeschlagen: %s", e)
            return diff

    async def _generate_recommendations_ai(
        self, competitors: list[dict], profiles: list[str], recent_changes: list[str]
    ) -> list[dict]:
        """Leitet aus Wettbewerberprofilen + aktuellen Änderungen konkrete Handlungsempfehlungen ab."""
        lines = [f"Analysiertes Unternehmen: {self.company_name}\n"]
        for comp, profile in zip(competitors, profiles):
            lines.append(f"### {comp.get('name', '?')}")
            lines.append(format_competitor_card(comp))
            if profile:
                lines.append(profile)
            lines.append("")

        if recent_changes:
            lines.append("### Aktuelle Änderungen bei Wettbewerbern")
            lines.extend(recent_changes)

        try:
            result = await ai_json("\n".join(lines), system=RECOMMENDATIONS_SYSTEM_PROMPT)
        except Exception as e:
            log.warning("Handlungsempfehlungen fehlgeschlagen: %s", e)
            return []

        if not isinstance(result, list):
            log.warning("KI hat für Handlungsempfehlungen kein Array zurückgegeben: %s", type(result))
            return []
        return result

    def _format_recommendations(self, recommendations: list[dict]) -> str:
        """Formatiert die Handlungsempfehlungen als übersichtliche Liste."""
        priority_icons = {"hoch": "🔴", "mittel": "🟡", "niedrig": "🟢"}
        lines = [f"Konkrete Handlungsempfehlungen für **{self.company_name}**:\n"]
        for i, rec in enumerate(recommendations, 1):
            icon = priority_icons.get(str(rec.get("priority", "")).lower(), "⚪")
            category = rec.get("category", "Sonstiges")
            lines.append(f"{i}. {icon} **{rec.get('action', '?')}** _({category})_")
            reason = rec.get("reason", "")
            if reason:
                lines.append(f"   {reason}")
            lines.append("")
        return "\n".join(lines)

    async def fetch_data(self) -> list[dict]:
        if not self.company_name:
            return [{
                "title": "Keine Firma angegeben",
                "description": "Bitte gib einen Firmennamen in den Einstellungen an.",
                "url": "",
                "event_type": "info",
                "is_info": True,
            }]

        # 1. Wettbewerber laden (Cache oder KI)
        competitors, profiles = await self._load_or_refresh_competitors()
        self._competitors = competitors

        if not competitors:
            return [{
                "title": "Keine Wettbewerber gefunden",
                "description": f"Die KI konnte keine Wettbewerber für '{self.company_name}' identifizieren.",
                "url": "",
                "event_type": "info",
                "is_info": True,
            }]

        results = []

        # 2. Marktübersicht
        overview_lines = [f"Wettbewerbsanalyse für **{self.company_name}** — {len(competitors)} Wettbewerber:\n"]
        for comp in competitors:
            overview_lines.append(format_competitor_card(comp))
            overview_lines.append("")
        results.append({
            "title": f"Marktübersicht: {self.company_name}",
            "description": "\n".join(overview_lines),
            "url": "",
            "event_type": "market_overview",
            "is_overview": True,
        })

        # 3. Detaillierte Profile
        for comp, profile in zip(competitors, profiles):
            if profile:
                results.append({
                    "title": f"Profil: {comp.get('name', '?')}",
                    "description": profile,
                    "url": comp.get("url", ""),
                    "event_type": "competitor_profile",
                    "is_profile": True,
                    "competitor_data": comp,
                })

        # 4. Webseiten scrapen
        targets = []
        for comp in competitors:
            url = comp.get("url", "")
            if not url:
                continue
            targets.append(ScrapingTarget(
                url=url,
                name=comp.get("name", url),
                selector="main",
                event_type="competitor_change",
            ))

        if targets:
            with get_session() as db:
                known_hashes = load_content_hashes(db)
                known_content = load_content_texts(db)

            source = WebScraperSource(
                targets=targets,
                known_hashes=known_hashes,
                known_content=known_content,
            )
            events = await source.fetch()

            with get_session() as db:
                for url, text in source.updated_content.items():
                    new_hash = source.known_hashes.get(url, "")
                    save_content_hash(db, url, new_hash, content_text=text)
                db.commit()

            for e in events:
                entry = {
                    "title": e.title,
                    "description": e.description,
                    "url": e.url,
                    "event_type": e.event_type,
                    "timestamp": e.timestamp.isoformat(),
                    **e.raw_data,
                }

                diff = e.raw_data.get("diff", "")
                if diff and e.event_type not in ("baseline", "error"):
                    ai_summary = await self._summarize_change(
                        e.raw_data.get("target_name", ""),
                        e.url,
                        diff,
                    )
                    entry["ai_summary"] = ai_summary
                    entry["description"] = ai_summary

                results.append(entry)

        # 5. Handlungsempfehlungen aus Wettbewerberprofilen + aktuellen Änderungen ableiten
        recent_changes = [
            f"- {r.get('title')}: {r.get('ai_summary')}"
            for r in results
            if r.get("event_type") == "competitor_change" and r.get("ai_summary")
        ]
        recommendations = await self._generate_recommendations_ai(competitors, profiles, recent_changes)
        if recommendations:
            results.insert(0, {
                "title": f"Handlungsempfehlungen für {self.company_name}",
                "description": self._format_recommendations(recommendations),
                "url": "",
                "event_type": "recommendations",
                "is_recommendations": True,
                "recommendations": recommendations,
            })

        return results

    def process_data(self, raw_data: list[dict]) -> list[ReportItem]:
        items = []
        for entry in raw_data:
            is_baseline = entry.get("is_baseline", False)
            is_error = entry.get("event_type") == "error"
            is_overview = entry.get("is_overview", False)
            is_profile = entry.get("is_profile", False)
            is_info = entry.get("is_info", False)
            is_recommendations = entry.get("is_recommendations", False)

            if is_overview:
                category = "important"
            elif is_profile or is_error or is_baseline or is_info:
                category = "info"
            else:
                category = "critical"

            keep_full_text = is_overview or is_profile or is_recommendations

            items.append(ReportItem(
                title=entry["title"],
                category=category,
                summary=entry["description"] if keep_full_text else entry["description"][:2000],
                source_url=entry.get("url", ""),
                metadata={
                    "event_type": entry.get("event_type"),
                    "ai_summary": entry.get("ai_summary"),
                    "content_hash": entry.get("content_hash"),
                    "competitor_data": entry.get("competitor_data"),
                    "recommendations": entry.get("recommendations"),
                },
            ))
        return items

    def generate_report(self, items: list[ReportItem]) -> Report:
        return Report(
            module_name=self.name,
            title=f"KI-Wettbewerbsanalyse – {self.company_name or 'Kein Unternehmen'}",
            items=items,
        )
