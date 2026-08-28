"""Editierbare Plan-Limits (Modul-Anzahl, KI-Token-Deckel pro Monat).

Die Werte können über das Admin-UI (/admin/plan-config) angepasst werden, ohne
Redeploy. Fehlt für einen Plan eine DB-Zeile (z.B. direkt nach dem Deploy dieses
Features), gelten die Code-Defaults unten.
"""

from sqlalchemy.orm import Session

from core.models import PlanConfig

PLANS = ("free", "basic", "pro")

DEFAULT_MODULE_LIMITS: dict[str, int] = {
    "free": 1,
    "basic": 1,
    "pro": 99,
}

# None = kein Limit.
DEFAULT_AI_TOKEN_LIMITS: dict[str, int | None] = {
    "free": 50_000,
    "basic": 300_000,
    "pro": 2_000_000,
}


def get_module_limit(db: Session, plan: str) -> int:
    row = db.query(PlanConfig).filter(PlanConfig.plan == plan).first()
    if row:
        return row.module_limit
    return DEFAULT_MODULE_LIMITS.get(plan, 0)


def get_ai_token_limit(db: Session, plan: str) -> int | None:
    row = db.query(PlanConfig).filter(PlanConfig.plan == plan).first()
    if row:
        return row.ai_token_limit
    return DEFAULT_AI_TOKEN_LIMITS.get(plan)


def get_all(db: Session) -> dict[str, dict]:
    """Effektive Werte (DB-Override oder Default) für alle bekannten Pläne – für die Admin-UI."""
    rows = {r.plan: r for r in db.query(PlanConfig).all()}
    result = {}
    for plan in PLANS:
        row = rows.get(plan)
        result[plan] = {
            "module_limit": row.module_limit if row else DEFAULT_MODULE_LIMITS.get(plan, 0),
            "ai_token_limit": row.ai_token_limit if row else DEFAULT_AI_TOKEN_LIMITS.get(plan),
        }
    return result


def set_config(db: Session, plan: str, module_limit: int, ai_token_limit: int | None) -> None:
    row = db.query(PlanConfig).filter(PlanConfig.plan == plan).first()
    if row:
        row.module_limit = module_limit
        row.ai_token_limit = ai_token_limit
    else:
        db.add(PlanConfig(plan=plan, module_limit=module_limit, ai_token_limit=ai_token_limit))
