"""Speichert Rohdaten und verarbeitete Daten in die Datenbank."""

import logging

from sqlalchemy.orm import Session

from core.base_module import ReportItem
from core.models import Event, ProcessedData, RawData

log = logging.getLogger(__name__)


def store_raw_data(db: Session, module: str, source: str, data: list[dict]) -> list[int]:
    """Speichert Rohdaten und gibt die IDs zurück."""
    ids = []
    for entry in data:
        row = RawData(module=module, source=source, data=entry)
        db.add(row)
        db.flush()
        ids.append(row.id)
    log.info("Stored %d raw_data rows for %s", len(ids), module)
    return ids


def store_processed_data(
    db: Session,
    module: str,
    items: list[ReportItem],
    raw_data_ids: list[int],
) -> None:
    """Speichert verarbeitete Daten."""
    for item in items:
        row = ProcessedData(
            module=module,
            raw_data_id=raw_data_ids[0] if raw_data_ids else None,
            category=item.category,
            title=item.title,
            summary=item.summary,
            extra_data=item.metadata,
        )
        db.add(row)
    log.info("Stored %d processed_data rows for %s", len(items), module)


def store_event(db: Session, module: str, event_type: str, payload: dict) -> int:
    """Speichert ein Event und gibt die ID zurück."""
    row = Event(module=module, event_type=event_type, payload=payload)
    db.add(row)
    db.flush()
    return row.id
