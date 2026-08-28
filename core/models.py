from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base

# --- Data Pipeline Models (Phase 1) ---

class RawData(Base):
    __tablename__ = "raw_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module: Mapped[str] = mapped_column(String(100), index=True)
    source: Mapped[str] = mapped_column(String(255))
    data: Mapped[dict] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ProcessedData(Base):
    __tablename__ = "processed_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module: Mapped[str] = mapped_column(String(100), index=True)
    raw_data_id: Mapped[int] = mapped_column(Integer, ForeignKey("raw_data.id"))
    category: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module: Mapped[str] = mapped_column(String(100), index=True)
    event_type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# --- Unified Event Pipeline (Phase 3) ---

class NormalizedEventRow(Base):
    """Alle Datenquellen in einem einheitlichen Format."""
    __tablename__ = "normalized_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dedup_key: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(50), index=True)   # github | cve | rss | scrape
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=True)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime)
    relevance_score: Mapped[int] = mapped_column(Integer, default=0)
    severity: Mapped[str] = mapped_column(String(20), default="low")
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ContentHash(Base):
    """Speichert Hashes für Web-Scraping Dedup."""
    __tablename__ = "content_hashes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String(1000), unique=True, index=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# --- User & SaaS Models (Phase 2) ---

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    subscription: Mapped["Subscription"] = relationship(back_populates="user", uselist=False)
    modules: Mapped[list["UserModule"]] = relationship(back_populates="user")
    preferences: Mapped[list["UserPreference"]] = relationship(back_populates="user")
    reports: Mapped[list["ReportHistory"]] = relationship(back_populates="user")
    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(back_populates="user")


class OAuthAccount(Base):
    """Verknüpfung eines Users mit einem Social-Login-Anbieter (Google, Microsoft, ...)."""
    __tablename__ = "oauth_accounts"
    __table_args__ = (UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_account"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    provider: Mapped[str] = mapped_column(String(30))          # google | microsoft | facebook | apple | github
    provider_user_id: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="oauth_accounts")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True)
    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str] = mapped_column(String(255), nullable=True)
    plan: Mapped[str] = mapped_column(String(50), default="free")  # free | basic | pro
    status: Mapped[str] = mapped_column(String(50), default="active")  # active | past_due | cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="subscription")


class UserModule(Base):
    __tablename__ = "user_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    module_name: Mapped[str] = mapped_column(String(100))

    user: Mapped["User"] = relationship(back_populates="modules")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    key: Mapped[str] = mapped_column(String(100))  # z.B. "watched_repos"
    value: Mapped[dict] = mapped_column(JSONB)      # z.B. ["fastapi/fastapi", "django/django"]

    user: Mapped["User"] = relationship(back_populates="preferences")


class CompetitorProfile(Base):
    """Gecachte Wettbewerber-Profile aus der KI-Analyse."""
    __tablename__ = "competitor_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), index=True)
    competitor_name: Mapped[str] = mapped_column(String(255))
    competitor_url: Mapped[str] = mapped_column(String(1000))
    competitor_data: Mapped[dict] = mapped_column(JSONB)
    ai_profile: Mapped[str | None] = mapped_column(Text, nullable=True)
    needs_refresh: Mapped[bool] = mapped_column(Boolean, default=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ReportHistory(Base):
    __tablename__ = "report_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    module: Mapped[str] = mapped_column(String(100))
    content_md: Mapped[str] = mapped_column(Text)
    content_html: Mapped[str] = mapped_column(Text)
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="reports")
