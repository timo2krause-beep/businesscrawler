"""Scheduler: Generiert Reports für zahlende Nutzer und sendet E-Mails."""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core import registry
from core.database import get_session, init_db
from core.email import send_report_email
from core.models import ReportHistory, Subscription, User, UserModule, UserPreference
from core.personalization import build_personalized_module
from core.report_renderer import render_html, render_markdown
from modules.cve_monitor import CVEMonitor
from modules.ki_wettbewerb import KIWettbewerbMonitor
from modules.review_monitor import ReviewMonitor
from modules.rss_monitor import RSSMonitor
from modules.social_sentiment import SocialSentimentMonitor
from modules.tech_stack_monitor import TechStackMonitor
from modules.wettbewerbs_monitor import WettbewerbsMonitor

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def generate_user_reports():
    """Generiert personalisierte Reports für alle zahlenden User."""
    with get_session() as db:
        # Alle aktiven, zahlenden Subscriptions
        subs = (
            db.query(Subscription)
            .filter(Subscription.status == "active", Subscription.plan != "free")
            .all()
        )

        for sub in subs:
            user = db.query(User).get(sub.user_id)
            if not user:
                continue

            user_modules = db.query(UserModule).filter(UserModule.user_id == user.id).all()
            prefs = {
                p.key: p.value
                for p in db.query(UserPreference).filter(UserPreference.user_id == user.id).all()
            }

            for um in user_modules:
                try:
                    module = registry.get_module(um.module_name)
                except KeyError:
                    log.warning("Modul %s nicht registriert", um.module_name)
                    continue

                # Personalisierung: eigene Instanz pro User
                personalized = build_personalized_module(um.module_name, prefs)
                if personalized:
                    module = personalized

                try:
                    report = await module.run(persist=True)
                    md = render_markdown(report)
                    html = render_html(report)

                    # In History speichern
                    db.add(ReportHistory(
                        user_id=user.id,
                        module=um.module_name,
                        content_md=md,
                        content_html=html,
                    ))

                    # E-Mail senden
                    send_report_email(
                        to=user.email,
                        subject=f"[Scraper] {report.title}",
                        html_body=html,
                    )

                    log.info("Report für User %s, Modul %s erstellt", user.email, um.module_name)
                except Exception:
                    log.exception("Fehler bei Report für User %d, Modul %s", user.id, um.module_name)


def main():
    init_db()
    registry.register(TechStackMonitor())
    registry.register(CVEMonitor())
    registry.register(RSSMonitor())
    registry.register(WettbewerbsMonitor())
    registry.register(KIWettbewerbMonitor())
    registry.register(SocialSentimentMonitor())
    registry.register(ReviewMonitor())

    scheduler = AsyncIOScheduler()
    # Wöchentlich Montags um 8:00
    scheduler.add_job(generate_user_reports, "cron", day_of_week="mon", hour=8)
    scheduler.start()

    log.info("Scheduler gestartet. Strg+C zum Beenden.")
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    main()
