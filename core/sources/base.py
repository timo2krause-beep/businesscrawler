"""Basis-Interface für alle Data Sources."""

from abc import ABC, abstractmethod

from core.events import NormalizedEvent


class BaseSource(ABC):
    """Jede Datenquelle implementiert dieses Interface."""

    name: str = "base"

    @abstractmethod
    async def fetch(self) -> list[NormalizedEvent]:
        """Holt Daten und gibt normalisierte Events zurück."""
        ...
