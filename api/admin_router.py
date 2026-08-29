"""Admin Endpoints: User-Übersicht, Stats und Plan-Konfiguration."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.schemas import (
    AdminUserResponse,
    AIPromptInfo,
    AIPromptUpdateRequest,
    AIPromptVersionInfo,
    AIRoutingTaskInfo,
    AIRoutingUpdateRequest,
    PlanConfigItem,
    StatsResponse,
)
from auth.dependencies import require_admin
from core.ai_prompts import get_default_prompt, get_effective_prompt, is_overridden
from core.ai_prompts import get_history as get_prompt_history_versions
from core.ai_prompts import reset_to_default as reset_prompt_to_default
from core.ai_prompts import save_version as save_prompt_version
from core.ai_routing import PROVIDERS as AI_PROVIDERS
from core.ai_routing import TASKS as AI_ROUTING_TASKS
from core.ai_routing import get_all as get_all_ai_routing
from core.ai_routing import set_provider as set_ai_provider
from core.ai_usage import current_period_start, get_monthly_tokens
from core.database import get_db
from core.models import AIPromptVersion, AIUsageLog, ReportHistory, Subscription, User
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


@router.get("/prompts", response_model=dict[str, AIPromptInfo])
def get_prompts(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Aktuelle System-Prompts pro Task (DB-Override oder Code-Default)."""
    return {
        task_key: AIPromptInfo(
            module=module,
            label=label,
            prompt=get_effective_prompt(db, task_key),
            is_override=is_overridden(db, task_key),
        )
        for task_key, (module, label) in AI_ROUTING_TASKS.items()
    }


@router.put("/prompts/{task_key}")
def update_prompt(
    task_key: str,
    req: AIPromptUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if task_key not in AI_ROUTING_TASKS:
        raise HTTPException(status_code=400, detail=f"Unbekannter Task '{task_key}'")
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt darf nicht leer sein")

    save_prompt_version(db, task_key, req.prompt, admin.id)
    db.commit()
    return {"detail": f"Prompt für '{task_key}' gespeichert"}


@router.post("/prompts/{task_key}/reset")
def reset_prompt(task_key: str, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    if task_key not in AI_ROUTING_TASKS:
        raise HTTPException(status_code=400, detail=f"Unbekannter Task '{task_key}'")

    reset_prompt_to_default(db, task_key)
    db.commit()
    return {"detail": f"Prompt für '{task_key}' zurückgesetzt", "prompt": get_default_prompt(task_key)}


@router.get("/prompts/{task_key}/history", response_model=list[AIPromptVersionInfo])
def get_prompt_history(task_key: str, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    if task_key not in AI_ROUTING_TASKS:
        raise HTTPException(status_code=400, detail=f"Unbekannter Task '{task_key}'")

    versions = get_prompt_history_versions(db, task_key)
    author_ids = {v.created_by for v in versions if v.created_by}
    authors = {}
    if author_ids:
        authors = {u.id: u.email for u in db.query(User).filter(User.id.in_(author_ids)).all()}

    return [
        AIPromptVersionInfo(
            id=v.id,
            prompt=v.prompt_text,
            created_at=v.created_at,
            created_by_email=authors.get(v.created_by),
        )
        for v in versions
    ]


@router.post("/prompts/{task_key}/restore/{version_id}")
def restore_prompt_version(
    task_key: str,
    version_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if task_key not in AI_ROUTING_TASKS:
        raise HTTPException(status_code=400, detail=f"Unbekannter Task '{task_key}'")

    version = (
        db.query(AIPromptVersion)
        .filter(AIPromptVersion.id == version_id, AIPromptVersion.task_key == task_key)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version nicht gefunden")

    save_prompt_version(db, task_key, version.prompt_text, admin.id)
    db.commit()
    return {"detail": "Version wiederhergestellt", "prompt": version.prompt_text}


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
