"""Persistenz für das Event-System: Speichern und Laden von Events."""

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.events import NormalizedEvent
from core.models import ContentHash, NormalizedEventRow

log = logging.getLogger(__name__)


def store_events(db: Session, events: list[NormalizedEvent]) -> int:
    """Speichert Events in die DB. Gibt Anzahl neuer Events zurück."""
    stored = 0
    for event in events:
        row = NormalizedEventRow(
            dedup_key=event.dedup_key,
            source=event.source,
            event_type=event.event_type,
            title=event.title[:500],
            description=event.description,
            url=event.url,
            event_timestamp=event.timestamp,
            relevance_score=event.relevance_score,
            severity=event.severity,
            raw_data=event.raw_data,
        )
        db.add(row)
        try:
            db.flush()
            stored += 1
        except IntegrityError:
            db.rollback()
            log.debug("Event bereits vorhanden: %s", event.dedup_key)

    log.info("EventStore: %d/%d Events gespeichert", stored, len(events))
    return stored


def load_known_dedup_keys(db: Session) -> set[str]:
    """Lädt alle bekannten dedup_keys für die Engine."""
    rows = db.query(NormalizedEventRow.dedup_key).all()
    return {r[0] for r in rows}


def load_content_hashes(db: Session) -> dict[str, str]:
    """Lädt gespeicherte Content-Hashes für den Web-Scraper."""
    rows = db.query(ContentHash).all()
    return {r.url: r.content_hash for r in rows}


def load_content_texts(db: Session) -> dict[str, str]:
    """Lädt gespeicherte Content-Texte für Diff-Berechnung."""
    rows = db.query(ContentHash).filter(ContentHash.content_text.isnot(None)).all()
    return {r.url: r.content_text for r in rows}


def save_content_hash(db: Session, url: str, content_hash: str, content_text: str | None = None) -> None:
    """Speichert oder aktualisiert einen Content-Hash und optional den Text."""
    existing = db.query(ContentHash).filter(ContentHash.url == url).first()
    if existing:
        existing.content_hash = content_hash
        if content_text is not None:
            existing.content_text = content_text
    else:
        db.add(ContentHash(url=url, content_hash=content_hash, content_text=content_text))


def get_events_by_source(
    db: Session,
    source: str | None = None,
    min_score: int = 0,
    limit: int = 100,
) -> list[NormalizedEventRow]:
    """Events aus der DB laden, optional gefiltert."""
    q = db.query(NormalizedEventRow).filter(
        NormalizedEventRow.relevance_score >= min_score
    )
    if source:
        q = q.filter(NormalizedEventRow.source == source)
    return q.order_by(NormalizedEventRow.ingested_at.desc()).limit(limit).all()


def get_event_stats(db: Session) -> dict:
    """Statistiken über gespeicherte Events."""
    from sqlalchemy import func

    total = db.query(func.count(NormalizedEventRow.id)).scalar()
    by_source = dict(
        db.query(NormalizedEventRow.source, func.count(NormalizedEventRow.id))
        .group_by(NormalizedEventRow.source)
        .all()
    )
    by_severity = dict(
        db.query(NormalizedEventRow.severity, func.count(NormalizedEventRow.id))
        .group_by(NormalizedEventRow.severity)
        .all()
    )
    avg_score = db.query(func.avg(NormalizedEventRow.relevance_score)).scalar()

    return {
        "total_events": total or 0,
        "by_source": by_source,
        "by_severity": by_severity,
        "avg_relevance_score": round(avg_score or 0, 1),
    }
