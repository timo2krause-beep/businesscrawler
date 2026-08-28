"""KI-Token-Verbrauch erfassen und pro User einen monatlichen Deckel durchsetzen.

core/ai_service.py ruft record_usage() nach jedem KI-Call auf. Das ist außerhalb
eines track()-Blocks ein No-op, damit Module nicht wissen müssen, ob gerade
getrackt wird. api/module_router.py und scheduler.py umschließen einen kompletten
Modul-Lauf mit track() und schreiben das Ergebnis danach als einen Log-Eintrag weg.
"""

import contextvars
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from core.models import AIUsageLog


@dataclass
class UsageAccumulator:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def add(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


_current: contextvars.ContextVar[UsageAccumulator | None] = contextvars.ContextVar(
    "ai_usage_accumulator", default=None
)


def record_usage(prompt_tokens: int, completion_tokens: int) -> None:
    """Von core/ai_service.py nach jedem KI-Call aufgerufen. No-op außerhalb von track()."""
    acc = _current.get()
    if acc is not None:
        acc.add(prompt_tokens, completion_tokens)


class track:
    """Context Manager: sammelt allen KI-Token-Verbrauch innerhalb des Blocks.

    with track() as usage:
        report = await module.run()
    # usage.total_tokens ist jetzt bekannt
    """

    def __enter__(self) -> UsageAccumulator:
        self._acc = UsageAccumulator()
        self._token = _current.set(self._acc)
        return self._acc

    def __exit__(self, *exc) -> None:
        _current.reset(self._token)


def current_period_start() -> datetime:
    """Beginn des laufenden Kalendermonats (UTC) – die Abrechnungsperiode für den Deckel."""
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def get_monthly_tokens(db: Session, user_id: int) -> int:
    """Summe aller KI-Tokens des Users im laufenden Kalendermonat."""
    total = (
        db.query(sa_func.coalesce(sa_func.sum(AIUsageLog.total_tokens), 0))
        .filter(AIUsageLog.user_id == user_id, AIUsageLog.created_at >= current_period_start())
        .scalar()
    )
    return int(total or 0)


def save_usage(db: Session, user_id: int, module: str, usage: UsageAccumulator) -> None:
    """Persistiert den Verbrauch eines Modul-Laufs. No-op wenn keine KI-Calls stattfanden."""
    if usage.total_tokens == 0:
        return
    db.add(AIUsageLog(
        user_id=user_id,
        module=module,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
    ))
