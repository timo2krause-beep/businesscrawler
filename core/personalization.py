"""Personalisierung: Baut aus User-Preferences eine passende Modul-Instanz.

Wird sowohl vom API-Router (api/module_router.py) als auch vom Scheduler
(scheduler.py) genutzt, damit beide Wege dieselbe Personalisierung anwenden.
"""

from core.base_module import BaseModule


def build_personalized_module(name: str, prefs: dict) -> BaseModule | None:
    """Baut eine personalisierte Modul-Instanz aus den User-Preferences.

    Gibt None zurück, wenn für dieses Modul keine passenden Preferences
    gesetzt sind — der Aufrufer soll dann die registrierte Default-Instanz nutzen.
    """
    if name == "tech_stack_monitor" and "watched_repos" in prefs:
        from modules.tech_stack_monitor import TechStackMonitor
        return TechStackMonitor(repos=prefs["watched_repos"])

    if name == "cve_monitor" and "cve_keywords" in prefs:
        from modules.cve_monitor import CVEMonitor
        return CVEMonitor(keywords=prefs["cve_keywords"])

    if name == "rss_monitor" and "rss_feeds" in prefs:
        from modules.rss_monitor import RSSMonitor
        return RSSMonitor(feeds=[(f["url"], f["name"]) for f in prefs["rss_feeds"]])

    if name == "wettbewerbs_monitor" and "scraping_targets" in prefs:
        from core.sources.web_scraper import ScrapingTarget
        from modules.wettbewerbs_monitor import WettbewerbsMonitor
        targets = [ScrapingTarget.from_dict(t) for t in prefs["scraping_targets"]]
        return WettbewerbsMonitor(targets=targets)

    if name == "ki_wettbewerb" and ("company_name" in prefs or "ki_company_name" in prefs):
        from modules.ki_wettbewerb import KIWettbewerbMonitor
        return KIWettbewerbMonitor(
            company_name=prefs.get("company_name") or prefs.get("ki_company_name", ""),
            location=prefs.get("company_location", ""),
            company_size=prefs.get("company_size", ""),
        )

    if name == "social_sentiment" and ("company_name" in prefs or "sentiment_company" in prefs):
        from modules.social_sentiment import SocialSentimentMonitor
        return SocialSentimentMonitor(
            company_name=prefs.get("company_name") or prefs.get("sentiment_company", "")
        )

    if name == "review_monitor" and ("company_name" in prefs or "review_company" in prefs):
        from modules.review_monitor import ReviewMonitor
        company = prefs.get("company_name") or prefs.get("review_company", "")
        platforms = prefs.get("company_platforms")
        return ReviewMonitor(
            company_name=company,
            platforms=platforms if isinstance(platforms, list) else None,
            location=prefs.get("company_location", ""),
        )

    return None
