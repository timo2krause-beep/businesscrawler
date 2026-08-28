"""Data Source Clients – holen Rohdaten und normalisieren zu Events."""

from core.sources.cve_source import CVESource
from core.sources.github_source import GitHubSource
from core.sources.rss_source import RSSSource
from core.sources.web_scraper import WebScraperSource

__all__ = ["CVESource", "GitHubSource", "RSSSource", "WebScraperSource"]
