#!/usr/bin/env python3
"""Demo: Vollständiger SaaS-Flow – Register → Abo → Modul → Report."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from auth.security import hash_password
from core import registry
from core.database import get_session, init_db
from core.models import (
    Event,
    ProcessedData,
    RawData,
    ReportHistory,
    Subscription,
    User,
    UserModule,
    UserPreference,
)
from core.report_renderer import render_html, render_markdown
from modules.tech_stack_monitor import TechStackMonitor


async def main():
    print("=" * 60)
    print("SCRAPER PLATFORM – SaaS Demo Flow")
    print("=" * 60)

    # 1. DB initialisieren
    print("\n[1] Datenbank initialisieren...")
    init_db()
    registry.register(TechStackMonitor())
    print("    Tabellen erstellt.")

    with get_session() as db:
        # 2. User registrieren
        print("\n[2] User registrieren: demo@example.com")
        existing = db.query(User).filter(User.email == "demo@example.com").first()
        if existing:
            user = existing
            print(f"    User existiert bereits (ID: {user.id})")
        else:
            user = User(email="demo@example.com", password_hash=hash_password("demo1234"))
            db.add(user)
            db.flush()
            # Free Subscription anlegen
            db.add(Subscription(user_id=user.id, plan="free", status="active"))
            db.flush()
            print(f"    User erstellt (ID: {user.id})")

        # 3. Auf Pro upgraden (simuliert Stripe Checkout)
        print("\n[3] Upgrade auf Pro-Plan (simuliert)...")
        sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
        sub.plan = "pro"
        sub.status = "active"
        sub.stripe_customer_id = "cus_demo_123"
        db.flush()
        print(f"    Plan: {sub.plan}, Status: {sub.status}")

        # 4. Modul abonnieren
        print("\n[4] Modul 'tech_stack_monitor' abonnieren...")
        existing_mod = (
            db.query(UserModule)
            .filter(UserModule.user_id == user.id, UserModule.module_name == "tech_stack_monitor")
            .first()
        )
        if not existing_mod:
            db.add(UserModule(user_id=user.id, module_name="tech_stack_monitor"))
            db.flush()
        print("    Modul abonniert.")

        # 5. Preferences setzen (personalisierte Repos)
        print("\n[5] Preferences setzen: eigene Repos überwachen...")
        pref = (
            db.query(UserPreference)
            .filter(UserPreference.user_id == user.id, UserPreference.key == "watched_repos")
            .first()
        )
        repos = ["fastapi/fastapi", "pydantic/pydantic", "encode/httpx"]
        if pref:
            pref.value = repos
        else:
            db.add(UserPreference(user_id=user.id, key="watched_repos", value=repos))
            db.flush()
        print(f"    Repos: {repos}")
        user_id = user.id

    # 6. Report generieren (personalisiert)
    print("\n[6] Personalisierter Report wird generiert...")
    monitor = TechStackMonitor(
        repos=["fastapi/fastapi", "pydantic/pydantic", "encode/httpx"],
        days_back=30,
    )
    report = await monitor.run(persist=True)
    md = render_markdown(report)
    html = render_html(report)

    # 7. Report in History speichern
    with get_session() as db:
        db.add(ReportHistory(
            user_id=user_id,
            module="tech_stack_monitor",
            content_md=md,
            content_html=html,
        ))

    # 8. Report anzeigen
    print(f"\n{'─' * 60}")
    print(md)
    print(f"{'─' * 60}")

    print(f"\n{len(report.items)} Items gefunden")
    print(f"  Kritisch:  {len(report.critical_items)}")
    print(f"  Wichtig:   {len(report.important_items)}")
    print(f"  Info:      {len(report.info_items)}")

    # 9. DB Stats
    with get_session() as db:
        print("\nDatenbank-Statistiken:")
        print(f"  Users:          {db.query(User).count()}")
        print(f"  Subscriptions:  {db.query(Subscription).filter(Subscription.plan != 'free').count()} (zahlend)")
        print(f"  User-Module:    {db.query(UserModule).count()}")
        print(f"  Reports:        {db.query(ReportHistory).count()}")
        print(f"  Raw Data:       {db.query(RawData).count()}")
        print(f"  Processed:      {db.query(ProcessedData).count()}")
        print(f"  Events:         {db.query(Event).count()}")

    # HTML-Report speichern
    out = Path("report_preview.html")
    out.write_text(html)
    print(f"\nHTML-Report: {out.absolute()}")
    print("\n✓ Demo abgeschlossen!")


if __name__ == "__main__":
    asyncio.run(main())
