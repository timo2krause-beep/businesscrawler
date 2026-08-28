"""Pydantic Schemas für die API."""

from datetime import datetime

from pydantic import BaseModel, EmailStr

# --- Auth ---

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    is_admin: bool
    created_at: datetime
    plan: str | None = None
    modules: list[str] = []

    model_config = {"from_attributes": True}


# --- Subscriptions ---

class CheckoutRequest(BaseModel):
    plan: str  # "basic" | "pro"


class CheckoutResponse(BaseModel):
    checkout_url: str


class SubscriptionResponse(BaseModel):
    plan: str
    status: str
    stripe_customer_id: str | None

    model_config = {"from_attributes": True}


# --- Modules ---

class ModuleSubscribeRequest(BaseModel):
    module_name: str


class ModuleListResponse(BaseModel):
    modules: list[str]


class ModuleRunResponse(BaseModel):
    module: str
    title: str
    item_count: int
    markdown: str
    report_id: int | None = None


# --- Preferences ---

class PreferenceSet(BaseModel):
    key: str
    value: dict | list | str


class PreferenceResponse(BaseModel):
    key: str
    value: dict | list | str

    model_config = {"from_attributes": True}


# --- Reports ---

class ReportResponse(BaseModel):
    id: int
    module: str
    content_md: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Admin ---

class AdminUserResponse(BaseModel):
    id: int
    email: str
    is_admin: bool
    plan: str | None
    status: str | None
    module_count: int
    created_at: datetime


class StatsResponse(BaseModel):
    total_users: int
    active_subscriptions: int
    total_reports: int
