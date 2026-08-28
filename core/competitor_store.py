"""Persistenz für Wettbewerber-Profile: Caching und Refresh-Trigger."""

import logging

from sqlalchemy.orm import Session

from core.models import CompetitorProfile

log = logging.getLogger(__name__)


def load_competitors(db: Session, company_name: str, active_only: bool = True) -> list[CompetitorProfile]:
    """Lädt alle gecachten Wettbewerber für ein Unternehmen."""
    q = db.query(CompetitorProfile).filter(CompetitorProfile.company_name == company_name.lower())
    if active_only:
        q = q.filter(CompetitorProfile.is_active == True)
    return q.all()


def save_competitor(
    db: Session,
    company_name: str,
    competitor_data: dict,
    ai_profile: str | None = None,
) -> CompetitorProfile:
    """Speichert oder aktualisiert ein Wettbewerber-Profil."""
    name_lower = company_name.lower()
    comp_name = competitor_data.get("name", "")

    existing = (
        db.query(CompetitorProfile)
        .filter(
            CompetitorProfile.company_name == name_lower,
            CompetitorProfile.competitor_name == comp_name,
        )
        .first()
    )

    if existing:
        existing.competitor_data = competitor_data
        existing.competitor_url = competitor_data.get("url", "")
        if ai_profile:
            existing.ai_profile = ai_profile
        existing.needs_refresh = False
        log.debug("Wettbewerber aktualisiert: %s → %s", company_name, comp_name)
        return existing

    row = CompetitorProfile(
        company_name=name_lower,
        competitor_name=comp_name,
        competitor_url=competitor_data.get("url", ""),
        competitor_data=competitor_data,
        ai_profile=ai_profile,
        needs_refresh=False,
    )
    db.add(row)
    log.info("Neuer Wettbewerber gespeichert: %s → %s", company_name, comp_name)
    return row


def needs_refresh(db: Session, company_name: str) -> bool:
    """Prüft ob ein Refresh nötig ist (keine Daten oder Trigger gesetzt)."""
    profiles = load_competitors(db, company_name)
    if not profiles:
        return True
    return any(p.needs_refresh for p in profiles)


def trigger_refresh(db: Session, company_name: str) -> int:
    """Markiert alle Profile eines Unternehmens zum Refresh. Gibt Anzahl zurück."""
    rows = (
        db.query(CompetitorProfile)
        .filter(CompetitorProfile.company_name == company_name.lower())
        .all()
    )
    for r in rows:
        r.needs_refresh = True
    count = len(rows)
    log.info("Refresh getriggert für %s (%d Profile)", company_name, count)
    return count


def trigger_refresh_all(db: Session) -> int:
    """Markiert ALLE Profile zum Refresh. Gibt Anzahl zurück."""
    count = (
        db.query(CompetitorProfile)
        .update({CompetitorProfile.needs_refresh: True})
    )
    log.info("Refresh für alle Profile getriggert (%d)", count)
    return count
