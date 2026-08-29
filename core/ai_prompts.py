"""Admin-editierbare System-Prompts pro Task: Versionshistorie + Code-Default-Fallback.

Jede Task hat einen Code-Default (die Prompt-Konstante im jeweiligen Modul). Speichert ein
Admin eine Änderung, landet sie als neue Zeile in ai_prompt_versions – die Historie ist
append-only, sodass ein fehlerhafter Edit jederzeit zurückgerollt werden kann.
"""

from sqlalchemy import desc
from sqlalchemy.orm import Session

from core.models import AIPromptVersion

_DEFAULT_PROMPTS: dict[str, str] | None = None


def _defaults() -> dict[str, str]:
    """Sammelt die Code-Default-Prompts aus den Modulen (lazy, damit core/ nicht beim
    Import bereits von modules/ abhängt)."""
    global _DEFAULT_PROMPTS
    if _DEFAULT_PROMPTS is None:
        from modules.ki_wettbewerb.module import (
            COMPETITOR_SYSTEM_PROMPT,
            DIFF_SYSTEM_PROMPT,
            PROFILE_SYSTEM_PROMPT,
            RECOMMENDATIONS_SYSTEM_PROMPT,
        )
        from modules.review_monitor.module import REVIEW_ANALYSIS_PROMPT
        from modules.social_media_generator.module import SOCIAL_POSTS_SYSTEM_PROMPT
        from modules.social_sentiment.module import (
            NEWSLETTER_SYSTEM_PROMPT,
            SENTIMENT_SYSTEM_PROMPT,
        )

        _DEFAULT_PROMPTS = {
            "ki_wettbewerb.identify_competitors": COMPETITOR_SYSTEM_PROMPT,
            "ki_wettbewerb.build_profile": PROFILE_SYSTEM_PROMPT,
            "ki_wettbewerb.diff_analysis": DIFF_SYSTEM_PROMPT,
            "ki_wettbewerb.recommendations": RECOMMENDATIONS_SYSTEM_PROMPT,
            "social_media_generator.posts": SOCIAL_POSTS_SYSTEM_PROMPT,
            "social_sentiment.sentiment": SENTIMENT_SYSTEM_PROMPT,
            "social_sentiment.newsletter": NEWSLETTER_SYSTEM_PROMPT,
            "review_monitor.analysis": REVIEW_ANALYSIS_PROMPT,
        }
    return _DEFAULT_PROMPTS


def get_default_prompt(task_key: str) -> str:
    return _defaults().get(task_key, "")


def _latest_version(db: Session, task_key: str) -> AIPromptVersion | None:
    return (
        db.query(AIPromptVersion)
        .filter(AIPromptVersion.task_key == task_key)
        .order_by(desc(AIPromptVersion.id))
        .first()
    )


def get_effective_prompt_or_default(db: Session, task_key: str, code_default: str) -> str:
    """Für ai_service.py: nutzt den vom Call-Site übergebenen Code-Default, ohne modules/
    zu importieren."""
    row = _latest_version(db, task_key)
    return row.prompt_text if row else code_default


def get_effective_prompt(db: Session, task_key: str) -> str:
    """Für die Admin-UI: nutzt den zentral gesammelten Code-Default."""
    return get_effective_prompt_or_default(db, task_key, get_default_prompt(task_key))


def is_overridden(db: Session, task_key: str) -> bool:
    return _latest_version(db, task_key) is not None


def get_history(db: Session, task_key: str, limit: int = 20) -> list[AIPromptVersion]:
    return (
        db.query(AIPromptVersion)
        .filter(AIPromptVersion.task_key == task_key)
        .order_by(desc(AIPromptVersion.id))
        .limit(limit)
        .all()
    )


def save_version(db: Session, task_key: str, prompt_text: str, user_id: int | None) -> AIPromptVersion:
    version = AIPromptVersion(task_key=task_key, prompt_text=prompt_text, created_by=user_id)
    db.add(version)
    db.flush()
    return version


def reset_to_default(db: Session, task_key: str) -> None:
    """Löscht alle gespeicherten Versionen – die Task fällt zurück auf den Code-Default."""
    db.query(AIPromptVersion).filter(AIPromptVersion.task_key == task_key).delete()
