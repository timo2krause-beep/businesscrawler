"""Social-Login Endpoints: Google, Microsoft, Facebook, GitHub, Apple."""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from auth.oauth_providers import (
    PROVIDERS,
    OAuthError,
    OAuthUserInfo,
    build_authorize_url,
    create_state,
    fetch_user_info,
    is_configured,
    verify_state,
)
from auth.security import create_access_token
from config.settings import settings
from core.database import get_db
from core.models import OAuthAccount, Subscription, User

router = APIRouter(prefix="/auth/oauth", tags=["OAuth"])


@router.get("/providers")
def list_providers():
    """Welche Login-Anbieter sind serverseitig konfiguriert? Steuert, welche Buttons das Frontend zeigt."""
    return {"providers": [p for p in PROVIDERS if is_configured(p)]}


@router.get("/{provider}/login")
def oauth_login(provider: str):
    if provider not in PROVIDERS:
        return RedirectResponse(f"{settings.frontend_url}/login?oauth_error=Unbekannter+Anbieter")
    if not is_configured(provider):
        return RedirectResponse(f"{settings.frontend_url}/login?oauth_error=Anbieter+nicht+konfiguriert")
    return RedirectResponse(build_authorize_url(provider, create_state()))


def _find_or_create_user(db: Session, provider: str, info: OAuthUserInfo) -> User:
    account = (
        db.query(OAuthAccount)
        .filter(OAuthAccount.provider == provider, OAuthAccount.provider_user_id == info.provider_user_id)
        .first()
    )
    if account:
        return account.user

    user = db.query(User).filter(User.email == info.email).first() if info.email else None
    if not user:
        email = info.email or f"{provider}-{info.provider_user_id}@no-email.oauth.local"
        user = User(email=email, password_hash=None)
        db.add(user)
        db.flush()
        db.add(Subscription(user_id=user.id, plan="free", status="active"))

    db.add(OAuthAccount(user_id=user.id, provider=provider, provider_user_id=info.provider_user_id, email=info.email))
    db.commit()
    return user


async def _complete_login(provider: str, code: str | None, state: str | None, db: Session) -> RedirectResponse:
    try:
        if not code or not state:
            raise OAuthError("Fehlender code- oder state-Parameter")
        verify_state(state)
        info = await fetch_user_info(provider, code)
        user = _find_or_create_user(db, provider, info)
        token = create_access_token(user.id, user.email)
        # Token im URL-Fragment statt Query-Parameter, damit es nicht an Server/Logs geschickt wird.
        return RedirectResponse(f"{settings.frontend_url}/oauth/callback#token={token}")
    except OAuthError as exc:
        return RedirectResponse(f"{settings.frontend_url}/login?oauth_error={quote(str(exc))}")


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if error:
        return RedirectResponse(f"{settings.frontend_url}/login?oauth_error={quote(error)}")
    return await _complete_login(provider, code, state, db)


@router.post("/apple/callback")
async def apple_callback(
    code: str | None = Form(None),
    state: str | None = Form(None),
    error: str | None = Form(None),
    db: Session = Depends(get_db),
):
    if error:
        return RedirectResponse(f"{settings.frontend_url}/login?oauth_error={quote(error)}")
    return await _complete_login("apple", code, state, db)
