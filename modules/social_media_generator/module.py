"""Social-Media-Post-Generator: Erstellt fertige, sofort postbare Social-Media-Vorlagen.

Eigenständiges Folgeprodukt zur KI-Wettbewerbsanalyse (ki_wettbewerb), damit es unabhängig
abonniert, ausgeführt und (später) separat bepreist werden kann. Nutzt dafür die bereits
gecachten Wettbewerberprofile aus core/competitor_store.py – kein eigenes Scraping nötig.
"""

import logging

from core.ai_service import ai_json
from core.base_module import BaseModule, Report, ReportItem
from core.competitor_store import format_competitor_card, load_competitors
from core.database import get_session

log = logging.getLogger(__name__)

SOCIAL_POSTS_SYSTEM_PROMPT = """Du bist ein Social-Media-Texter für kleine und mittlere Unternehmen.
Du bekommst eine Wettbewerbsanalyse (Profile der wichtigsten Wettbewerber).
Erstelle 5 SOFORT NUTZBARE Social-Media-Post-Vorlagen (primär für Instagram/Facebook), mit denen sich
das analysierte Unternehmen gezielt von den Wettbewerbern abheben kann.

Anforderungen an jeden Post:
- Fertiger Copy-Text auf Deutsch, direkt postbar (keine Platzhalter wie "[hier einfügen]")
- Bezug zu einer konkreten Stärke des Unternehmens gegenüber einem bestimmten Wettbewerber
  (z.B. dessen Schwäche, Preismodell oder Angebotslücke)
- 3-5 passende Hashtags
- Ein konkreter Vorschlag für das Bild-/Videomotiv

Antworte ausschließlich als JSON-Array mit diesem Format:
[
  {
    "caption": "Fertiger Post-Text inkl. Call-to-Action",
    "hashtags": ["#Hashtag1", "#Hashtag2"],
    "image_idea": "Konkreter Vorschlag für Bild oder Video",
    "based_on": "Kurzer Hinweis, worauf sich der Post bezieht (z.B. welcher Wettbewerber)"
  }
]

Wichtig:
- Erfinde keine Fakten über das Unternehmen oder die Wettbewerber, die dir nicht gegeben wurden
- Schreibe im Ton eines echten kleinen Unternehmens, nicht wie ein Großkonzern
- Nur JSON ausgeben, kein anderer Text"""


class SocialMediaGenerator(BaseModule):
    name = "social_media_generator"
    description = "Erstellt fertige, sofort postbare Social-Media-Vorlagen aus deiner Wettbewerbsanalyse"

    def __init__(self, company_name: str = ""):
        self.company_name = company_name

    async def _generate_posts_ai(self, competitors: list[dict], profiles: list[str]) -> list[dict]:
        """Erstellt fertige Social-Media-Post-Vorlagen basierend auf gecachten Wettbewerberdaten."""
        lines = [f"Analysiertes Unternehmen: {self.company_name}\n"]
        for comp, profile in zip(competitors, profiles):
            lines.append(f"### {comp.get('name', '?')}")
            lines.append(format_competitor_card(comp))
            if profile:
                lines.append(profile)
            lines.append("")

        try:
            result = await ai_json("\n".join(lines), system=SOCIAL_POSTS_SYSTEM_PROMPT, task="social_media_generator.posts")
        except Exception as e:
            log.warning("Social-Media-Vorlagen fehlgeschlagen: %s", e)
            return []

        if not isinstance(result, list):
            log.warning("KI hat für Social-Media-Vorlagen kein Array zurückgegeben: %s", type(result))
            return []
        return result

    def _format_posts(self, posts: list[dict]) -> str:
        """Formatiert die Social-Media-Vorlagen als copy-paste-fertige Liste."""
        lines = [f"Fertige Social-Media-Post-Vorlagen für **{self.company_name}** — direkt kopierbar:\n"]
        for i, post in enumerate(posts, 1):
            based_on = post.get("based_on", "")
            heading = f"### Post {i}"
            if based_on:
                heading += f" _(Bezug: {based_on})_"
            lines.append(heading)
            lines.append("```")
            lines.append(post.get("caption", ""))
            hashtags = post.get("hashtags", [])
            if hashtags:
                lines.append("")
                lines.append(" ".join(hashtags))
            lines.append("```")
            image_idea = post.get("image_idea", "")
            if image_idea:
                lines.append(f"📷 Bildidee: {image_idea}")
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

        with get_session() as db:
            cached = load_competitors(db, self.company_name)
            competitors = [row.competitor_data for row in cached]
            profiles = [row.ai_profile or "" for row in cached]

        if not competitors:
            return [{
                "title": "Keine Wettbewerberdaten gefunden",
                "description": (
                    f"Für '{self.company_name}' liegen noch keine Wettbewerberdaten vor. "
                    "Führe zuerst die KI-Wettbewerbsanalyse aus."
                ),
                "url": "",
                "event_type": "info",
                "is_info": True,
            }]

        posts = await self._generate_posts_ai(competitors, profiles)
        if not posts:
            return [{
                "title": "Keine Social-Media-Vorlagen erstellt",
                "description": "Die KI konnte keine Vorlagen generieren. Bitte später erneut versuchen.",
                "url": "",
                "event_type": "info",
                "is_info": True,
            }]

        return [{
            "title": f"Social-Media-Vorlagen für {self.company_name}",
            "description": self._format_posts(posts),
            "url": "",
            "event_type": "social_posts",
            "social_posts": posts,
        }]

    def process_data(self, raw_data: list[dict]) -> list[ReportItem]:
        items = []
        for entry in raw_data:
            is_info = entry.get("is_info", False)
            items.append(ReportItem(
                title=entry["title"],
                category="info" if is_info else "important",
                summary=entry["description"],
                source_url=entry.get("url", ""),
                metadata={
                    "event_type": entry.get("event_type"),
                    "social_posts": entry.get("social_posts"),
                },
            ))
        return items

    def generate_report(self, items: list[ReportItem]) -> Report:
        return Report(
            module_name=self.name,
            title=f"Social-Media-Vorlagen – {self.company_name or 'Kein Unternehmen'}",
            items=items,
        )
