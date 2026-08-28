"""Admin Endpoints: User-Übersicht und Stats."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.schemas import AdminUserResponse, StatsResponse
from auth.dependencies import require_admin
from core.database import get_db
from core.models import ReportHistory, Subscription, User

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=list[AdminUserResponse])
def list_users(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        AdminUserResponse(
            id=u.id,
            email=u.email,
            is_admin=u.is_admin,
            plan=u.subscription.plan if u.subscription else None,
            status=u.subscription.status if u.subscription else None,
            module_count=len(u.modules),
            created_at=u.created_at,
        )
        for u in users
    ]


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return StatsResponse(
        total_users=db.query(User).count(),
        active_subscriptions=db.query(Subscription)
            .filter(Subscription.status == "active", Subscription.plan != "free")
            .count(),
        total_reports=db.query(ReportHistory).count(),
    )
