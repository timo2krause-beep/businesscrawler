"""Web Scraper Source: Scraped Webseiten, erkennt Änderungen und erzeugt Diffs."""

import difflib
import hashlib
import logging
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup

from core.events import NormalizedEvent
from core.sources.base import BaseSource

log = logging.getLogger(__name__)


class ScrapingTarget:
    """Definition einer zu scrapenden Seite."""

    def __init__(
        self,
        url: str,
        name: str,
        selector: str = "body",
        event_type: str = "price_change",
    ):
        self.url = url
        self.name = name
        self.selector = selector
        self.event_type = event_type

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "name": self.name,
            "selector": self.selector,
            "event_type": self.event_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScrapingTarget":
        return cls(
            url=data["url"],
            name=data.get("name", data["url"]),
            selector=data.get("selector", "body"),
            event_type=data.get("event_type", "price_change"),
        )


# Funktionierende Beispiel-Targets
DEFAULT_TARGETS = [
    ScrapingTarget(
        url="https://stripe.com/de/pricing",
        name="Stripe Pricing",
        selector="main",
        event_type="price_change",
    ),
    ScrapingTarget(
        url="https://docs.github.com/en/get-started/learning-about-github/githubs-plans",
        name="GitHub Plans",
        selector="main",
        event_type="price_change",
    ),
]


def _extract_text(html: str, selector: str) -> str:
    """Extrahiert Text aus HTML via CSS-Selector."""
    soup = BeautifulSoup(html, "html.parser")

    # Noise entfernen
    for tag in soup.select("script, style, nav, footer, header, noscript"):
        tag.decompose()

    element = soup.select_one(selector)
    if not element:
        # Fallback auf body
        element = soup.body or soup
    return element.get_text(separator="\n", strip=True)


def _compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _compute_diff(old_text: str, new_text: str) -> str:
    """Erzeugt einen lesbaren Diff zwischen altem und neuem Content."""
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    diff = list(difflib.unified_diff(old_lines, new_lines, n=1, lineterm=""))
    if not diff:
        return ""

    # Nur geänderte Zeilen extrahieren (max 500 Zeichen)
    changes = []
    for line in diff:
        if line.startswith("+") and not line.startswith("+++"):
            changes.append(f"  NEU: {line[1:].strip()}")
        elif line.startswith("-") and not line.startswith("---"):
            changes.append(f"  ALT: {line[1:].strip()}")

    return "\n".join(changes[:20])


class WebScraperSource(BaseSource):
    name = "scrape"

    def __init__(
        self,
        targets: list[ScrapingTarget] | None = None,
        known_hashes: dict[str, str] | None = None,
        known_content: dict[str, str] | None = None,
    ):
        self.targets = targets or DEFAULT_TARGETS
        self.known_hashes = known_hashes or {}
        self.known_content = known_content or {}  # URL → letzter Text (für Diff)
        self.updated_content: dict[str, str] = {}  # Nach dem Scrape aktualisiert

    async def fetch(self) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []

        async with httpx.AsyncClient(
            timeout=20.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
            },
            follow_redirects=True,
        ) as client:
            for target in self.targets:
                result = await self._scrape_target(client, target)
                if result:
                    events.append(result)

        return events

    async def _scrape_target(
        self, client: httpx.AsyncClient, target: ScrapingTarget
    ) -> NormalizedEvent | None:
        try:
            resp = await client.get(target.url)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            log.warning("Scrape %s: HTTP %d", target.name, e.response.status_code)
            return NormalizedEvent(
                source="scrape",
                event_type="error",
                title=f"Scrape fehlgeschlagen: {target.name}",
                description=f"HTTP {e.response.status_code} beim Abruf von {target.url}",
                url=target.url,
                timestamp=datetime.now(UTC),
                raw_data={"target_name": target.name, "error": str(e), "status_code": e.response.status_code},
            )
        except httpx.RequestError as e:
            log.warning("Scrape %s: %s", target.name, e)
            return None

        text = _extract_text(resp.text, target.selector)
        if not text or len(text) < 10:
            log.warning("Selector '%s' liefert keinen Content auf %s", target.selector, target.url)
            return None

        content_hash = _compute_hash(text)
        old_hash = self.known_hashes.get(target.url)
        old_text = self.known_content.get(target.url, "")

        # Content immer aktualisieren
        self.known_hashes[target.url] = content_hash
        self.known_content[target.url] = text[:5000]
        self.updated_content[target.url] = text[:5000]

        if old_hash is None:
            # Erster Scrape – Baseline
            log.info("Baseline gespeichert: %s (%d Zeichen)", target.name, len(text))
            return NormalizedEvent(
                source="scrape",
                event_type="baseline",
                title=f"Baseline: {target.name}",
                description=f"Seite erfasst ({len(text)} Zeichen). Änderungen werden ab jetzt erkannt.",
                url=target.url,
                timestamp=datetime.now(UTC),
                raw_data={
                    "target_name": target.name,
                    "content_hash": content_hash,
                    "char_count": len(text),
                    "is_baseline": True,
                    "preview": text[:300],
                },
            )

        if old_hash == content_hash:
            log.debug("Keine Änderung: %s", target.name)
            return None

        # Änderung erkannt!
        diff = _compute_diff(old_text, text) if old_text else "Diff nicht verfügbar (kein alter Content)"
        log.info("ÄNDERUNG erkannt: %s", target.name)

        return NormalizedEvent(
            source="scrape",
            event_type=target.event_type,
            title=f"Änderung erkannt: {target.name}",
            description=f"Inhalt auf {target.url} hat sich geändert.\n\nÄnderungen:\n{diff}",
            url=target.url,
            timestamp=datetime.now(UTC),
            raw_data={
                "target_name": target.name,
                "content_hash": content_hash,
                "old_hash": old_hash,
                "diff": diff,
                "new_char_count": len(text),
                "preview": text[:300],
            },
        )
