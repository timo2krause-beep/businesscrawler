"""KI-Provider-Routing pro Prompt/Task: admin-konfigurierbar, mit Code-Default 'auto'."""

from sqlalchemy.orm import Session

from core.models import AIRoutingConfig

PROVIDERS = ("auto", "gemini", "openrouter")
DEFAULT_PROVIDER = "auto"

# task_key -> (Modul, Beschreibung des Prompts) für die Admin-UI
TASKS: dict[str, tuple[str, str]] = {
    "ki_wettbewerb.identify_competitors": ("KI-Wettbewerbsanalyse", "Wettbewerber identifizieren"),
    "ki_wettbewerb.build_profile": ("KI-Wettbewerbsanalyse", "Wettbewerber-Profil erstellen"),
    "ki_wettbewerb.diff_analysis": ("KI-Wettbewerbsanalyse", "Änderungen analysieren"),
    "ki_wettbewerb.recommendations": ("KI-Wettbewerbsanalyse", "Handlungsempfehlungen"),
    "social_media_generator.posts": ("Social-Media-Vorlagen", "Post-Vorlagen erstellen"),
    "social_sentiment.sentiment": ("Social Sentiment", "Stimmungsanalyse"),
    "social_sentiment.newsletter": ("Social Sentiment", "Zusammenfassung"),
    "review_monitor.analysis": ("Bewertungs-Monitor", "Bewertungs-Analyse"),
}


def get_provider(db: Session, task_key: str) -> str:
    row = db.query(AIRoutingConfig).filter(AIRoutingConfig.task_key == task_key).first()
    return row.provider if row else DEFAULT_PROVIDER


def get_all(db: Session) -> dict[str, dict]:
    rows = {r.task_key: r.provider for r in db.query(AIRoutingConfig).all()}
    return {
        key: {"module": module, "label": label, "provider": rows.get(key, DEFAULT_PROVIDER)}
        for key, (module, label) in TASKS.items()
    }


def set_provider(db: Session, task_key: str, provider: str) -> None:
    row = db.query(AIRoutingConfig).filter(AIRoutingConfig.task_key == task_key).first()
    if row:
        row.provider = provider
    else:
        db.add(AIRoutingConfig(task_key=task_key, provider=provider))
