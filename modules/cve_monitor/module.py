"""CVE Monitor: Überwacht Sicherheitslücken aus der NVD-Datenbank."""

from core.base_module import BaseModule, Report, ReportItem
from core.events import score_event
from core.sources.cve_source import CVESource

DEFAULT_KEYWORDS = ["python", "fastapi", "django", "postgresql", "node"]


class CVEMonitor(BaseModule):
    name = "cve_monitor"
    description = "Überwacht CVE/NVD-Datenbank auf Sicherheitslücken"

    def __init__(self, keywords: list[str] | None = None, days_back: int = 14):
        self.keywords = keywords or DEFAULT_KEYWORDS
        self.days_back = days_back

    async def fetch_data(self) -> list[dict]:
        source = CVESource(keywords=self.keywords, days_back=self.days_back)
        events = await source.fetch()
        # Score berechnen und als dicts zurückgeben
        for e in events:
            score_event(e)
        return [
            {
                "title": e.title,
                "description": e.description,
                "url": e.url,
                "score": e.relevance_score,
                "severity": e.severity,
                "timestamp": e.timestamp.isoformat(),
                **e.raw_data,
            }
            for e in events
        ]

    def process_data(self, raw_data: list[dict]) -> list[ReportItem]:
        items = []
        for entry in raw_data:
            severity = entry.get("cvss_severity", "MEDIUM")
            score = entry.get("score", 50)

            if severity in ("CRITICAL", "HIGH"):
                category = "critical"
            elif severity == "MEDIUM":
                category = "important"
            else:
                category = "info"

            items.append(ReportItem(
                title=entry["title"],
                category=category,
                summary=f"**{severity}** (CVSS Score: {entry.get('cvss_score', 'N/A')})\n\n{entry['description'][:300]}",
                source_url=entry["url"],
                metadata={"cve_id": entry.get("cve_id"), "cvss_score": entry.get("cvss_score"), "relevance": score},
            ))

        items.sort(key=lambda x: x.metadata.get("relevance", 0), reverse=True)
        return items

    def generate_report(self, items: list[ReportItem]) -> Report:
        return Report(
            module_name=self.name,
            title="CVE Security Monitor – Wochenbericht",
            items=items,
        )
