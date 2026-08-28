"""Report Endpoints: History und Zugriff."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.schemas import ReportResponse
from auth.dependencies import get_current_user
from core.database import get_db
from core.models import ReportHistory, User

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("", response_model=list[ReportResponse])
def list_reports(
    module: str | None = None,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Listet die Report-History des Users auf."""
    q = db.query(ReportHistory).filter(ReportHistory.user_id == user.id)
    if module:
        q = q.filter(ReportHistory.module == module)
    return q.order_by(ReportHistory.created_at.desc()).limit(limit).all()


@router.get("/{report_id}")
def get_report(
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Gibt einen einzelnen Report zurück (Markdown + HTML)."""
    report = (
        db.query(ReportHistory)
        .filter(ReportHistory.id == report_id, ReportHistory.user_id == user.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report nicht gefunden")

    return {
        "id": report.id,
        "module": report.module,
        "content_md": report.content_md,
        "content_html": report.content_html,
        "raw_data": report.raw_data,
        "created_at": report.created_at.isoformat(),
    }
