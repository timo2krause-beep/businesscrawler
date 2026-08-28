from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config.settings import settings

engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Session:
    """FastAPI Dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_session() -> Session:
    """Context-Manager für Standalone-Nutzung (Scheduler, CLI)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Erstellt alle Tabellen. Für MVP ausreichend, später Alembic."""
    from core import models  # noqa: F401 – Models müssen importiert sein
    Base.metadata.create_all(bind=engine)

    # Manuelle Migrationen für neue Spalten
    from sqlalchemy import text
    with engine.connect() as conn:
        for stmt in [
            "ALTER TABLE competitor_profiles ADD COLUMN IF NOT EXISTS is_custom BOOLEAN DEFAULT false",
            "ALTER TABLE competitor_profiles ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true",
            "ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL",
        ]:
            conn.execute(text(stmt))
        conn.commit()
