"""GitHub Data Source: Releases + Security Advisories."""

import logging
import re
from datetime import UTC, datetime

import httpx

from config.settings import settings
from core.events import NormalizedEvent
from core.sources.base import BaseSource

log = logging.getLogger(__name__)

SEMVER_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


def _classify_release(prev_tag: str | None, new_tag: str) -> dict:
    """Gibt Flags für Major/Minor/Patch zurück."""
    if not prev_tag:
        return {"is_major": False, "is_minor": False, "is_patch": True}

    old = SEMVER_RE.search(prev_tag)
    new = SEMVER_RE.search(new_tag)
    if not old or not new:
        return {"is_major": False, "is_minor": False, "is_patch": True}

    o = tuple(int(x) for x in old.groups())
    n = tuple(int(x) for x in new.groups())

    return {
        "is_major": n[0] > o[0],
        "is_minor": n[1] > o[1] and n[0] == o[0],
        "is_patch": n[0] == o[0] and n[1] == o[1],
    }


class GitHubSource(BaseSource):
    name = "github"

    def __init__(self, repos: list[str]):
        self.repos = repos

    async def fetch(self) -> list[NormalizedEvent]:
        headers = {"Accept": "application/vnd.github+json"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        events: list[NormalizedEvent] = []

        async with httpx.AsyncClient(
            base_url="https://api.github.com", headers=headers, timeout=30.0
        ) as client:
            for repo in self.repos:
                events.extend(await self._fetch_releases(client, repo))
                events.extend(await self._fetch_advisories(client, repo))

        return events

    async def _fetch_releases(
        self, client: httpx.AsyncClient, repo: str
    ) -> list[NormalizedEvent]:
        events = []
        try:
            resp = await client.get(f"/repos/{repo}/releases", params={"per_page": 10})
            resp.raise_for_status()
            releases = resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            log.warning("GitHub releases %s: %s", repo, e)
            return []

        # Sortiere chronologisch für prev_tag Vergleich
        releases.sort(key=lambda r: r.get("published_at", ""))

        for i, rel in enumerate(releases):
            published = rel.get("published_at")
            if not published:
                continue

            tag = rel.get("tag_name", "")
            prev_tag = releases[i - 1].get("tag_name") if i > 0 else None
            flags = _classify_release(prev_tag, tag)
            body = (rel.get("body") or "")[:500]

            events.append(NormalizedEvent(
                source="github",
                event_type="release",
                title=f"{repo} {tag}",
                description=body,
                url=rel.get("html_url", ""),
                timestamp=datetime.fromisoformat(published.replace("Z", "+00:00")),
                raw_data={
                    "repo": repo,
                    "tag": tag,
                    "prerelease": rel.get("prerelease", False),
                    **flags,
                },
            ))

        log.info("GitHub: %d releases von %s", len(events), repo)
        return events

    async def _fetch_advisories(
        self, client: httpx.AsyncClient, repo: str
    ) -> list[NormalizedEvent]:
        """Holt Security Advisories (falls vorhanden)."""
        events = []
        try:
            resp = await client.get(
                f"/repos/{repo}/security-advisories",
                params={"per_page": 10, "state": "published"},
            )
            if resp.status_code == 404:
                return []  # Nicht alle Repos haben Advisories
            resp.raise_for_status()
            advisories = resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            log.debug("GitHub advisories %s: %s", repo, e)
            return []

        for adv in advisories:
            severity = (adv.get("severity") or "medium").upper()
            events.append(NormalizedEvent(
                source="github",
                event_type="security_advisory",
                title=f"[{severity}] {adv.get('summary', 'Security Advisory')} ({repo})",
                description=adv.get("description", "")[:500],
                url=adv.get("html_url", ""),
                timestamp=datetime.fromisoformat(
                    adv.get("published_at", datetime.now(UTC).isoformat())
                    .replace("Z", "+00:00")
                ),
                raw_data={"repo": repo, "severity": severity, "cve_id": adv.get("cve_id")},
            ))

        return events
