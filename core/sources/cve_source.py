"""CVE/NVD Data Source: Holt Sicherheitslücken von der National Vulnerability Database."""

import logging
from datetime import UTC, datetime, timedelta

import httpx

from core.events import NormalizedEvent
from core.sources.base import BaseSource

log = logging.getLogger(__name__)

NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"


class CVESource(BaseSource):
    name = "cve"

    def __init__(self, keywords: list[str] | None = None, days_back: int = 7):
        # Keywords um relevante CVEs zu finden (z.B. Framework-Namen)
        self.keywords = keywords or ["python", "fastapi", "django", "postgresql", "node"]
        self.days_back = days_back

    async def fetch(self) -> list[NormalizedEvent]:
        events: list[NormalizedEvent] = []
        now = datetime.now(UTC)
        start = now - timedelta(days=self.days_back)

        async with httpx.AsyncClient(timeout=30.0) as client:
            for keyword in self.keywords:
                events.extend(await self._search(client, keyword, start, now))

        return events

    async def _search(
        self,
        client: httpx.AsyncClient,
        keyword: str,
        start: datetime,
        end: datetime,
    ) -> list[NormalizedEvent]:
        events = []

        params = {
            "keywordSearch": keyword,
            "pubStartDate": start.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "pubEndDate": end.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "resultsPerPage": 20,
        }

        try:
            resp = await client.get(NVD_API, params=params)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            log.warning("NVD API Fehler für '%s': %s", keyword, e)
            return []

        for vuln in data.get("vulnerabilities", []):
            cve = vuln.get("cve", {})
            cve_id = cve.get("id", "")

            # Beschreibung extrahieren
            descriptions = cve.get("descriptions", [])
            desc = next(
                (d["value"] for d in descriptions if d.get("lang") == "en"),
                descriptions[0]["value"] if descriptions else "",
            )

            # CVSS Score und Severity
            metrics = cve.get("metrics", {})
            cvss_data = (
                metrics.get("cvssMetricV31", [{}])[0] if metrics.get("cvssMetricV31")
                else metrics.get("cvssMetricV2", [{}])[0] if metrics.get("cvssMetricV2")
                else {}
            )
            cvss_score = cvss_data.get("cvssData", {}).get("baseScore", 0)
            cvss_severity = cvss_data.get("cvssData", {}).get("baseSeverity", "MEDIUM")

            # Timestamp
            published = cve.get("published", "")
            try:
                ts = datetime.fromisoformat(published.replace("Z", "+00:00"))
            except ValueError:
                ts = datetime.now(UTC)

            # URL
            url = f"https://nvd.nist.gov/vuln/detail/{cve_id}"

            events.append(NormalizedEvent(
                source="cve",
                event_type="vulnerability",
                title=f"{cve_id}: {desc[:100]}",
                description=desc[:500],
                url=url,
                timestamp=ts,
                raw_data={
                    "cve_id": cve_id,
                    "cvss_score": cvss_score,
                    "cvss_severity": cvss_severity,
                    "keyword": keyword,
                },
            ))

        log.info("NVD: %d CVEs für '%s'", len(events), keyword)
        return events
