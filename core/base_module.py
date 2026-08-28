"""Basis-Interface für alle Module der Plattform."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

log = logging.getLogger(__name__)


@dataclass
class ReportItem:
    """Ein einzelner Eintrag im Report."""
    title: str
    category: str  # "critical" | "important" | "info" | "irrelevant"
    summary: str
    source_url: str = ""
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Report:
    """Ein generierter Report."""
    module_name: str
    title: str
    items: list[ReportItem]
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def critical_items(self) -> list[ReportItem]:
        return [i for i in self.items if i.category == "critical"]

    @property
    def important_items(self) -> list[ReportItem]:
        return [i for i in self.items if i.category == "important"]

    @property
    def info_items(self) -> list[ReportItem]:
        return [i for i in self.items if i.category == "info"]


class BaseModule(ABC):
    """Jedes Modul implementiert dieses Interface."""

    name: str = "base"
    description: str = ""

    @abstractmethod
    async def fetch_data(self) -> list[dict]:
        """Daten aus externen Quellen abrufen."""
        ...

    @abstractmethod
    def process_data(self, raw_data: list[dict]) -> list[ReportItem]:
        """Rohdaten analysieren und klassifizieren."""
        ...

    @abstractmethod
    def generate_report(self, items: list[ReportItem]) -> Report:
        """Report aus verarbeiteten Daten erstellen."""
        ...

    async def run(self, persist: bool = True) -> Report:
        """Kompletten Pipeline-Durchlauf: fetch → process → report.

        Bei persist=True werden Roh- und verarbeitete Daten in die DB geschrieben.
        """
        raw = await self.fetch_data()
        items = self.process_data(raw)
        report = self.generate_report(items)

        if persist:
            self._persist(raw, items)

        return report

    def _persist(self, raw_data: list[dict], items: list[ReportItem]) -> None:
        """Daten in die DB speichern. Fehler werden geloggt, brechen aber nicht ab."""
        try:
            from core.database import get_session
            from core.persistence import store_event, store_processed_data, store_raw_data

            with get_session() as db:
                raw_ids = store_raw_data(db, self.name, self.name, raw_data)
                store_processed_data(db, self.name, items, raw_ids)

                for item in items:
                    if item.category in ("critical", "important"):
                        store_event(db, self.name, f"new_{item.category}", {
                            "title": item.title,
                            "category": item.category,
                            "source_url": item.source_url,
                        })

            log.info("Daten für %s in DB gespeichert", self.name)
        except Exception:
            log.exception("DB-Persistenz fehlgeschlagen für %s (Report wird trotzdem erstellt)", self.name)
