"""Tech-Stack Monitor: Überwacht GitHub Releases und erkennt neue Versionen."""

import logging
import re
from datetime import UTC, datetime, timedelta

import httpx

from config.settings import settings
from core.base_module import BaseModule, Report, ReportItem

log = logging.getLogger(__name__)

# Repos die standardmäßig überwacht werden
DEFAULT_REPOS = [
    "fastapi/fastapi",
    "pallets/flask",
    "django/django",
    "psf/requests",
    "encode/httpx",
    "pydantic/pydantic",
    "sqlalchemy/sqlalchemy",
]

SEMVER_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


def classify_version_change(old_tag: str | None, new_tag: str) -> str:
    """Klassifiziert eine Versionsänderung basierend auf SemVer."""
    if old_tag is None:
        return "info"

    old = SEMVER_RE.search(old_tag)
    new = SEMVER_RE.search(new_tag)
    if not old or not new:
        return "info"

    old_parts = tuple(int(x) for x in old.groups())
    new_parts = tuple(int(x) for x in new.groups())

    if new_parts[0] > old_parts[0]:
        return "critical"  # Major version = potentielle Breaking Changes
    if new_parts[1] > old_parts[1]:
        return "important"  # Minor version = neue Features
    return "info"  # Patch = Bugfixes


def summarize_release(release: dict, category: str) -> str:
    """Erzeugt eine kurze Zusammenfassung basierend auf der Kategorie."""
    body = (release.get("body") or "")[:300]
    tag = release.get("tag_name", "")

    if category == "critical":
        return (
            f"**Major Release {tag}** – Potentielle Breaking Changes! "
            f"Vor dem Update Changelog prüfen.\n\n> {body}..."
        )
    if category == "important":
        return f"**Neues Minor Release {tag}** – Neue Features verfügbar.\n\n> {body}..."
    return f"Release {tag} veröffentlicht (Bugfixes/Patches).\n\n> {body}..."


class TechStackMonitor(BaseModule):
    name = "tech_stack_monitor"
    description = "Überwacht GitHub Releases für konfigurierte Repositories"

    def __init__(self, repos: list[str] | None = None, days_back: int = 7):
        self.repos = repos or DEFAULT_REPOS
        self.days_back = days_back

    async def fetch_data(self) -> list[dict]:
        """Ruft die neuesten Releases der konfigurierten Repos ab."""
        headers = {"Accept": "application/vnd.github+json"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        results = []
        async with httpx.AsyncClient(
            base_url="https://api.github.com",
            headers=headers,
            timeout=30.0,
        ) as client:
            for repo in self.repos:
                try:
                    resp = await client.get(f"/repos/{repo}/releases", params={"per_page": 5})
                    resp.raise_for_status()
                    releases = resp.json()
                    for r in releases:
                        r["_repo"] = repo
                    results.extend(releases)
                    log.info("Fetched %d releases für %s", len(releases), repo)
                except httpx.HTTPStatusError as e:
                    log.warning("Fehler bei %s: %s", repo, e.response.status_code)
                except httpx.RequestError as e:
                    log.warning("Request-Fehler bei %s: %s", repo, e)

        return results

    def process_data(self, raw_data: list[dict]) -> list[ReportItem]:
        """Filtert auf kürzliche Releases und klassifiziert sie."""
        cutoff = datetime.now(UTC) - timedelta(days=self.days_back)
        items = []

        # Gruppiere nach Repo, um vorherige Version zu kennen
        by_repo: dict[str, list[dict]] = {}
        for release in raw_data:
            repo = release.get("_repo", "unknown")
            by_repo.setdefault(repo, []).append(release)

        for repo, releases in by_repo.items():
            # Sortiere nach Datum (neueste zuerst)
            releases.sort(
                key=lambda r: r.get("published_at", ""),
                reverse=True,
            )

            for i, release in enumerate(releases):
                published = release.get("published_at")
                if not published:
                    continue

                pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
                if pub_date < cutoff:
                    continue

                tag = release.get("tag_name", "")
                prev_tag = releases[i + 1].get("tag_name") if i + 1 < len(releases) else None
                category = classify_version_change(prev_tag, tag)

                items.append(ReportItem(
                    title=f"{repo} {tag}",
                    category=category,
                    summary=summarize_release(release, category),
                    source_url=release.get("html_url", ""),
                    metadata={"repo": repo, "tag": tag, "prerelease": release.get("prerelease")},
                    timestamp=pub_date,
                ))

        # Sortiere: critical → important → info
        priority = {"critical": 0, "important": 1, "info": 2}
        items.sort(key=lambda x: (priority.get(x.category, 9), x.timestamp), reverse=False)

        return items

    def generate_report(self, items: list[ReportItem]) -> Report:
        return Report(
            module_name=self.name,
            title="Tech-Stack Monitor – Wochenbericht",
            items=items,
        )
