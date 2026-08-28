"""Module Endpoints: Auswahl, Ausführung, Personalisierung."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.schemas import (
    ModuleRunResponse,
    ModuleSubscribeRequest,
    PreferenceResponse,
    PreferenceSet,
)
from auth.dependencies import get_current_user
from core import registry
from core.database import get_db
from core.models import ReportHistory, User, UserModule, UserPreference
from core.personalization import build_personalized_module
from core.report_renderer import render_html, render_markdown
from payments.stripe_service import PLAN_LIMITS

router = APIRouter(prefix="/modules", tags=["Modules"])


@router.get("")
def list_modules():
    """Alle verfügbaren Module mit Beschreibung."""
    modules = []
    for name, mod in registry.all_modules().items():
        modules.append({
            "name": name,
            "description": mod.description,
        })
    return {"modules": modules}


@router.post("/subscribe")
def subscribe_to_module(
    req: ModuleSubscribeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """User abonniert ein Modul (begrenzt durch Plan)."""
    if req.module_name not in registry.list_modules():
        raise HTTPException(status_code=404, detail=f"Modul '{req.module_name}' nicht gefunden")

    plan = user.subscription.plan if user.subscription else "free"
    limit = PLAN_LIMITS.get(plan, 0)
    current_count = len(user.modules)

    if current_count >= limit:
        raise HTTPException(
            status_code=403,
            detail=f"Plan '{plan}' erlaubt max. {limit} Module. Upgrade auf Pro für mehr.",
        )

    # Prüfen ob bereits abonniert
    existing = (
        db.query(UserModule)
        .filter(UserModule.user_id == user.id, UserModule.module_name == req.module_name)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Modul bereits abonniert")

    db.add(UserModule(user_id=user.id, module_name=req.module_name))
    db.commit()
    return {"detail": f"Modul '{req.module_name}' abonniert"}


@router.delete("/subscribe/{module_name}")
def unsubscribe_from_module(
    module_name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(UserModule)
        .filter(UserModule.user_id == user.id, UserModule.module_name == module_name)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Modul nicht abonniert")
    db.delete(row)
    db.commit()
    return {"detail": f"Modul '{module_name}' abbestellt"}


@router.post("/{name}/run", response_model=ModuleRunResponse)
async def run_module(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Führt ein Modul für den User aus (mit Personalisierung)."""
    # Prüfe ob User das Modul abonniert hat
    subscribed = any(m.module_name == name for m in user.modules)
    if not subscribed:
        raise HTTPException(status_code=403, detail=f"Modul '{name}' nicht abonniert")

    try:
        module = registry.get_module(name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Personalisierung: User-Preferences auf das Modul anwenden
    prefs = {p.key: p.value for p in user.preferences}
    personalized = build_personalized_module(name, prefs)
    if personalized:
        module = personalized

    report = await module.run(persist=True)
    md = render_markdown(report)
    html = render_html(report)

    # Rohdaten aus Items extrahieren (Plattform-Stats, Ratings etc.)
    raw_data = _extract_raw_data(report)

    # Report in History speichern
    row = ReportHistory(
        user_id=user.id,
        module=name,
        content_md=md,
        content_html=html,
        raw_data=raw_data,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return ModuleRunResponse(
        module=report.module_name,
        title=report.title,
        item_count=len(report.items),
        markdown=md,
        report_id=row.id,
    )


# --- Preferences ---

@router.get("/preferences", response_model=list[PreferenceResponse])
def get_preferences(user: User = Depends(get_current_user)):
    return user.preferences


@router.put("/preferences")
def set_preference(
    pref: PreferenceSet,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Setzt eine User-Preference (z.B. watched_repos)."""
    existing = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == user.id, UserPreference.key == pref.key)
        .first()
    )
    if existing:
        existing.value = pref.value
    else:
        db.add(UserPreference(user_id=user.id, key=pref.key, value=pref.value))
    db.commit()
    return {"detail": f"Preference '{pref.key}' gespeichert"}


# --- Competitor Refresh Trigger ---

@router.post("/ki_wettbewerb/refresh")
def refresh_competitors(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Markiert Wettbewerber-Profile zum Refresh. Beim nächsten Report-Run werden sie neu per KI analysiert."""
    from core.competitor_store import trigger_refresh

    prefs = {p.key: p.value for p in user.preferences}
    company_name = prefs.get("company_name") or prefs.get("ki_company_name", "")
    if not company_name:
        raise HTTPException(status_code=400, detail="Kein Firmenname konfiguriert")

    count = trigger_refresh(db, company_name)
    db.commit()
    return {"detail": f"Refresh für {count} Wettbewerber-Profile getriggert", "count": count}


# --- Helper ---

def _extract_raw_data(report) -> dict | None:
    """Extrahiert strukturierte Rohdaten aus den Report-Items für die Historie."""
    platforms = []
    seen_platforms = set()
    stats = None

    for item in report.items:
        meta = item.metadata or {}

        # Sentiment / Review Stats (einmalig)
        if meta.get("stats") and not stats:
            stats = meta["stats"]

        # Nur Summary-Items mit avg_rating ODER review_count (keine Einzelreviews)
        platform = meta.get("platform")
        if not platform or platform in seen_platforms:
            continue
        if meta.get("avg_rating") is not None or meta.get("review_count") is not None:
            seen_platforms.add(platform)
            platforms.append({
                "platform": platform,
                "avg_rating": meta.get("avg_rating"),
                "review_count": meta.get("review_count"),
            })

    if stats:
        return {"type": "stats", "stats": stats, "platforms": platforms}

    if platforms:
        return {"type": "platforms", "platforms": platforms}

    return None
