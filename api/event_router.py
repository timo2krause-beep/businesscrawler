"""Event API: Zugriff auf das unified Event System."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from core.database import get_db
from core.event_store import get_event_stats, get_events_by_source
from core.models import User

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("")
def list_events(
    source: str | None = None,
    min_score: int = Query(0, ge=0, le=100),
    limit: int = Query(50, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = get_events_by_source(db, source=source, min_score=min_score, limit=limit)
    return [
        {
            "id": r.id,
            "source": r.source,
            "event_type": r.event_type,
            "title": r.title,
            "description": r.description[:200] if r.description else "",
            "url": r.url,
            "relevance_score": r.relevance_score,
            "severity": r.severity,
            "timestamp": r.event_timestamp.isoformat(),
            "ingested_at": r.ingested_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/stats")
def event_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_event_stats(db)
