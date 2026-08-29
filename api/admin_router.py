"""Admin Endpoints: User-Übersicht, Stats und Plan-Konfiguration."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.schemas import (
    AdminUserResponse,
    AIRoutingTaskInfo,
    AIRoutingUpdateRequest,
    PlanConfigItem,
    StatsResponse,
)
from auth.dependencies import require_admin
from core.ai_routing import PROVIDERS as AI_PROVIDERS
from core.ai_routing import TASKS as AI_ROUTING_TASKS
from core.ai_routing import get_all as get_all_ai_routing
from core.ai_routing import set_provider as set_ai_provider
from core.ai_usage import current_period_start, get_monthly_tokens
from core.database import get_db
from core.models import AIUsageLog, ReportHistory, Subscription, User
from core.plan_config import PLANS, get_ai_token_limit, set_config
from core.plan_config import get_all as get_all_plan_configs

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
            ai_tokens_used_month=get_monthly_tokens(db, u.id),
            ai_token_limit=get_ai_token_limit(db, u.subscription.plan if u.subscription else "free"),
        )
        for u in users
    ]


@router.get("/plan-config", response_model=dict[str, PlanConfigItem])
def get_plan_config(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Effektive Limits pro Plan (DB-Override oder Code-Default)."""
    return get_all_plan_configs(db)


@router.put("/plan-config/{plan}")
def update_plan_config(
    plan: str,
    req: PlanConfigItem,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    if plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Unbekannter Plan '{plan}'")
    if req.module_limit < 0:
        raise HTTPException(status_code=400, detail="Modul-Limit darf nicht negativ sein")
    if req.ai_token_limit is not None and req.ai_token_limit < 0:
        raise HTTPException(status_code=400, detail="Token-Limit darf nicht negativ sein")

    set_config(db, plan, req.module_limit, req.ai_token_limit)
    db.commit()
    return {"detail": f"Plan '{plan}' aktualisiert"}


@router.get("/ai-routing", response_model=dict[str, AIRoutingTaskInfo])
def get_ai_routing(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Aktuelle KI-Provider-Wahl pro Prompt/Task (DB-Override oder Code-Default 'auto')."""
    return get_all_ai_routing(db)


@router.put("/ai-routing/{task_key}")
def update_ai_routing(
    task_key: str,
    req: AIRoutingUpdateRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    if task_key not in AI_ROUTING_TASKS:
        raise HTTPException(status_code=400, detail=f"Unbekannter Task '{task_key}'")
    if req.provider not in AI_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unbekannter Provider '{req.provider}'")

    set_ai_provider(db, task_key, req.provider)
    db.commit()
    return {"detail": f"Routing für '{task_key}' aktualisiert"}


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    from sqlalchemy import func as sa_func

    total_ai_tokens_month = (
        db.query(sa_func.coalesce(sa_func.sum(AIUsageLog.total_tokens), 0))
        .filter(AIUsageLog.created_at >= current_period_start())
        .scalar()
    )

    return StatsResponse(
        total_users=db.query(User).count(),
        active_subscriptions=db.query(Subscription)
            .filter(Subscription.status == "active", Subscription.plan != "free")
            .count(),
        total_reports=db.query(ReportHistory).count(),
        total_ai_tokens_month=int(total_ai_tokens_month or 0),
    )
