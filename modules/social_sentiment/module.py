"""Social Sentiment Monitor: Sammelt Social-Media-Erwähnungen und erstellt KI-Stimmungsanalyse.

Quellen: Reddit, Hacker News, Google News, X/Twitter (via Nitter), TikTok.
"""

import logging
from datetime import UTC, datetime

from core.ai_service import ai_chat, ai_json
from core.base_module import BaseModule, Report, ReportItem
from core.sources.googlenews_source import fetch_googlenews_mentions
from core.sources.hackernews_source import fetch_hackernews_mentions
from core.sources.mastodon_source import fetch_mastodon_mentions
from core.sources.reddit_source import fetch_reddit_mentions
from core.sources.tiktok_source import fetch_tiktok_mentions
from core.sources.x_source import fetch_x_mentions
from core.sources.youtube_source import fetch_youtube_mentions

log = logging.getLogger(__name__)

SENTIMENT_SYSTEM_PROMPT = """Du bist ein Social-Media-Analyst. Analysiere die folgenden Posts/Artikel über ein Unternehmen.

Für jeden Post: Bewerte das Sentiment als "positiv", "neutral" oder "negativ".

Antworte als JSON-Array:
[
  {"index": 0, "sentiment": "positiv", "reason": "Kurze Begründung"},
  {"index": 1, "sentiment": "negativ", "reason": "Kurze Begründung"}
]

Nur JSON ausgeben."""

NEWSLETTER_SYSTEM_PROMPT = """Du bist ein professioneller Analyst und Newsletter-Autor.
Erstelle einen kompakten täglichen Newsletter auf Deutsch über die Social-Media-Stimmung zu einem Unternehmen.

Struktur:
## Stimmungsbild: [Firma]

### Zusammenfassung
2-3 Sätze: Gesamtstimmung heute, wichtigster Trend.

### Stimmungsbarometer
- Positiv: X%
- Neutral: X%
- Negativ: X%

### Plattform-Übersicht
Kurze Aufschlüsselung nach Plattform (Reddit, X/Twitter, TikTok, Hacker News, Google News) — wo wird am meisten diskutiert, wo ist die Stimmung am besten/schlechtesten?

### Wichtigste Themen
Top 3-5 Themen die diskutiert werden, mit Sentiment-Einordnung.

### Highlights
Die 3-5 relevantesten Posts/Artikel mit Plattform, Quelle, Kernaussage und Sentiment.

### Trend-Einschätzung
2-3 Sätze: Wie entwickelt sich die Stimmung? Worauf sollte das Unternehmen achten?

Schreibe klar, sachlich und geschäftsorientiert. Nutze Markdown-Formatierung."""

PLATFORM_LABELS = {
    "reddit": "Reddit",
    "hackernews": "Hacker News",
    "googlenews": "Google News",
    "x_twitter": "X/Twitter",
    "tiktok": "TikTok",
    "youtube": "YouTube",
    "mastodon": "Mastodon",
}


class SocialSentimentMonitor(BaseModule):
    name = "social_sentiment"
    description = "Social-Media-Stimmungsanalyse: Reddit, X/Twitter, TikTok, YouTube, Mastodon, Hacker News und Google News mit KI-Newsletter"

    def __init__(self, company_name: str = "", language: str = "de"):
        self.company_name = company_name
        self.language = language

    async def _collect_mentions(self) -> list[dict]:
        """Sammelt Erwähnungen aus allen Quellen."""
        log.info("Sammle Erwähnungen aus 7 Quellen für: %s", self.company_name)

        # Alle Quellen abfragen — jede darf fehlschlagen ohne den Rest zu blockieren
        sources = {
            "reddit": fetch_reddit_mentions(self.company_name, limit=20),
            "hackernews": fetch_hackernews_mentions(self.company_name, limit=15),
            "googlenews": fetch_googlenews_mentions(self.company_name, language=self.language, limit=15),
            "x_twitter": fetch_x_mentions(self.company_name, limit=15),
            "tiktok": fetch_tiktok_mentions(self.company_name, limit=10),
            "youtube": fetch_youtube_mentions(self.company_name, limit=10),
            "mastodon": fetch_mastodon_mentions(self.company_name, limit=15),
        }

        all_posts: list = []
        source_counts = {}
        for name, coro in sources.items():
            try:
                posts = await coro
                source_counts[name] = len(posts)
                all_posts.extend(posts)
            except Exception as e:
                log.warning("%s fehlgeschlagen: %s", name, e)
                source_counts[name] = 0

        log.info("Quellen-Ergebnis: %s", source_counts)

        all_mentions = []
        for event in all_posts:
            all_mentions.append({
                "platform": event.raw_data.get("platform", event.source),
                "title": event.title,
                "description": event.description[:300],
                "url": event.url,
                "timestamp": event.timestamp.isoformat(),
                "score": event.raw_data.get("score") or event.raw_data.get("points", 0),
                "num_comments": event.raw_data.get("num_comments", 0),
                "source_name": event.raw_data.get("source_name", ""),
                "subreddit": event.raw_data.get("subreddit", ""),
                "author": event.raw_data.get("author", ""),
                "play_count": event.raw_data.get("play_count", 0),
                "like_count": event.raw_data.get("like_count", 0),
            })

        # Nach Engagement sortieren
        all_mentions.sort(
            key=lambda x: (x.get("score", 0) + x.get("num_comments", 0) + x.get("play_count", 0)),
            reverse=True,
        )
        return all_mentions

    async def _analyze_sentiment(self, mentions: list[dict]) -> list[dict]:
        """Lässt die KI das Sentiment jedes Posts bewerten."""
        if not mentions:
            return []

        post_texts = []
        for i, m in enumerate(mentions):
            platform = PLATFORM_LABELS.get(m["platform"], m["platform"])
            post_texts.append(f"[{i}] ({platform}) {m['title']}: {m['description'][:200]}")

        prompt = (
            f"Unternehmen: {self.company_name}\n\n"
            f"Posts:\n" + "\n".join(post_texts)
        )

        try:
            sentiments = await ai_json(prompt, system=SENTIMENT_SYSTEM_PROMPT, task="social_sentiment.sentiment")
            if isinstance(sentiments, list):
                sentiment_map = {s["index"]: s for s in sentiments if "index" in s}
                for i, m in enumerate(mentions):
                    s = sentiment_map.get(i, {})
                    m["sentiment"] = s.get("sentiment", "neutral")
                    m["sentiment_reason"] = s.get("reason", "")
        except Exception as e:
            log.warning("Sentiment-Analyse fehlgeschlagen: %s", e)
            for m in mentions:
                m["sentiment"] = "neutral"
                m["sentiment_reason"] = ""

        return mentions

    async def _generate_newsletter(self, mentions: list[dict]) -> str:
        """Erstellt den KI-Newsletter basierend auf den analysierten Mentions."""
        if not mentions:
            return f"Keine Erwähnungen für '{self.company_name}' gefunden."

        total = len(mentions)
        pos = sum(1 for m in mentions if m.get("sentiment") == "positiv")
        neg = sum(1 for m in mentions if m.get("sentiment") == "negativ")
        neu = total - pos - neg

        # Plattform-Aufschlüsselung
        platform_stats = {}
        for m in mentions:
            p = m["platform"]
            if p not in platform_stats:
                platform_stats[p] = {"total": 0, "positiv": 0, "negativ": 0, "neutral": 0}
            platform_stats[p]["total"] += 1
            platform_stats[p][m.get("sentiment", "neutral")] += 1

        platform_lines = []
        for p, stats in platform_stats.items():
            label = PLATFORM_LABELS.get(p, p)
            platform_lines.append(
                f"  {label}: {stats['total']} Posts "
                f"({stats['positiv']} pos / {stats['neutral']} neu / {stats['negativ']} neg)"
            )

        post_summaries = []
        for m in mentions[:30]:
            platform = PLATFORM_LABELS.get(m["platform"], m["platform"])
            extra = ""
            if m.get("play_count"):
                extra = f", Views: {m['play_count']}"
            post_summaries.append(
                f"- [{platform}] {m['title']} "
                f"(Sentiment: {m.get('sentiment', '?')}, "
                f"Score: {m.get('score', 0)}, "
                f"Kommentare: {m.get('num_comments', 0)}{extra})\n"
                f"  {m['description'][:200]}\n"
                f"  Begründung: {m.get('sentiment_reason', '-')}"
            )

        prompt = (
            f"Unternehmen: {self.company_name}\n"
            f"Zeitraum: Letzte 7 Tage\n"
            f"Datum: {datetime.now(UTC).strftime('%d.%m.%Y')}\n\n"
            f"Statistik: {total} Erwähnungen — {pos} positiv, {neu} neutral, {neg} negativ\n\n"
            f"Plattform-Aufschlüsselung:\n" + "\n".join(platform_lines) + "\n\n"
            "Posts:\n" + "\n".join(post_summaries)
        )

        try:
            return await ai_chat(prompt, system=NEWSLETTER_SYSTEM_PROMPT, max_tokens=3000, task="social_sentiment.newsletter")
        except Exception as e:
            log.warning("Newsletter-Generierung fehlgeschlagen: %s", e)
            return f"Newsletter konnte nicht generiert werden: {e}"

    async def fetch_data(self) -> list[dict]:
        if not self.company_name:
            return [{
                "title": "Kein Unternehmen konfiguriert",
                "description": "Bitte gib einen Firmennamen in den Moduleinstellungen an.",
                "url": "",
                "category": "info",
            }]

        # 1. Erwähnungen sammeln
        mentions = await self._collect_mentions()

        if not mentions:
            return [{
                "title": f"Keine Erwähnungen für '{self.company_name}'",
                "description": "In den letzten 7 Tagen wurden keine Erwähnungen gefunden.",
                "url": "",
                "category": "info",
            }]

        # 2. Sentiment analysieren
        log.info("Analysiere Sentiment für %d Posts", len(mentions))
        mentions = await self._analyze_sentiment(mentions)

        # 3. Newsletter generieren
        log.info("Generiere Newsletter")
        newsletter = await self._generate_newsletter(mentions)

        # 4. Ergebnisse zusammenbauen
        total = len(mentions)
        pos = sum(1 for m in mentions if m.get("sentiment") == "positiv")
        neg = sum(1 for m in mentions if m.get("sentiment") == "negativ")
        neu = total - pos - neg

        # Plattform-Counts
        platform_counts = {}
        for m in mentions:
            p = m["platform"]
            platform_counts[p] = platform_counts.get(p, 0) + 1

        results = []

        # Newsletter als Haupt-Item
        results.append({
            "title": f"Stimmungsbild: {self.company_name}",
            "description": newsletter,
            "url": "",
            "category": "important",
            "is_newsletter": True,
            "stats": {
                "total": total,
                "positive": pos,
                "neutral": neu,
                "negative": neg,
                "platforms": platform_counts,
            },
        })

        # Top-Mentions als Einzel-Items
        for m in mentions[:15]:
            sentiment = m.get("sentiment", "neutral")
            emoji = {"positiv": "+", "negativ": "-", "neutral": "~"}.get(sentiment, "~")
            platform = PLATFORM_LABELS.get(m.get("platform", ""), m.get("platform", ""))

            desc_parts = [m["description"][:300]]
            desc_parts.append(f"\nSentiment: {sentiment} — {m.get('sentiment_reason', '')}")
            if m.get("play_count"):
                desc_parts.append(f"Views: {m['play_count']:,} | Likes: {m.get('like_count', 0):,}")

            results.append({
                "title": f"[{emoji}] ({platform}) {m['title'].removeprefix(f'{platform}: ').removeprefix('X: ').removeprefix('HN: ').removeprefix('TikTok: ').removeprefix('News: ')}",
                "description": "\n".join(desc_parts),
                "url": m.get("url", ""),
                "category": "info",
                "platform": m.get("platform"),
                "sentiment": sentiment,
                "score": m.get("score", 0),
                "num_comments": m.get("num_comments", 0),
            })

        return results

    def process_data(self, raw_data: list[dict]) -> list[ReportItem]:
        items = []
        for entry in raw_data:
            cat = entry.get("category", "info")
            items.append(ReportItem(
                title=entry["title"],
                category=cat,
                summary=entry["description"] if entry.get("is_newsletter") else entry["description"][:2000],
                source_url=entry.get("url", ""),
                metadata={
                    "platform": entry.get("platform"),
                    "sentiment": entry.get("sentiment"),
                    "score": entry.get("score"),
                    "num_comments": entry.get("num_comments"),
                    "stats": entry.get("stats"),
                    "is_newsletter": entry.get("is_newsletter", False),
                },
            ))
        return items

    def generate_report(self, items: list[ReportItem]) -> Report:
        return Report(
            module_name=self.name,
            title=f"Social Sentiment – {self.company_name or 'Nicht konfiguriert'}",
            items=items,
        )
