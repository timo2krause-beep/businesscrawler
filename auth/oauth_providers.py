"""OAuth2 'Login mit ...' für Google, Microsoft, Facebook, GitHub und Apple.

Google/Microsoft/Facebook/GitHub laufen über den klassischen OAuth2
Authorization-Code-Flow. Apple ("Sign in with Apple") weicht ab: response_mode
ist form_post (POST-Callback statt GET) und der client_secret ist kein
statischer String, sondern ein selbst signiertes ES256-JWT.
"""

import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
import jwt as pyjwt

from config.settings import settings

STATE_TTL_SECONDS = 600
PROVIDERS = ("google", "microsoft", "facebook", "github", "apple")

_STANDARD = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope": "openid email profile",
        "auth_extra": {"access_type": "offline", "prompt": "select_account"},
    },
    "microsoft": {
        "auth_url": f"https://login.microsoftonline.com/{settings.microsoft_oauth_tenant}/oauth2/v2.0/authorize",
        "token_url": f"https://login.microsoftonline.com/{settings.microsoft_oauth_tenant}/oauth2/v2.0/token",
        "userinfo_url": "https://graph.microsoft.com/oidc/userinfo",
        "scope": "openid email profile",
        "auth_extra": {},
    },
    "facebook": {
        "auth_url": "https://www.facebook.com/v19.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v19.0/oauth/access_token",
        "userinfo_url": "https://graph.facebook.com/me",
        "scope": "email public_profile",
        "auth_extra": {},
    },
    "github": {
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scope": "read:user user:email",
        "auth_extra": {},
    },
}


class OAuthError(Exception):
    """Fehler im OAuth-Ablauf – wird als Redirect mit Fehlermeldung ans Frontend gegeben."""


@dataclass
class OAuthUserInfo:
    provider_user_id: str
    email: str | None
    name: str | None


def is_configured(provider: str) -> bool:
    if provider == "apple":
        return bool(
            settings.apple_oauth_client_id
            and settings.apple_oauth_team_id
            and settings.apple_oauth_key_id
            and settings.apple_oauth_private_key
        )
    return bool(
        getattr(settings, f"{provider}_oauth_client_id", "")
        and getattr(settings, f"{provider}_oauth_client_secret", "")
    )


def create_state() -> str:
    """Signiertes, zeitlich begrenztes State-Token – schützt vor CSRF ohne Server-Session."""
    payload = {"nonce": secrets.token_urlsafe(16), "exp": int(time.time()) + STATE_TTL_SECONDS}
    return pyjwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_state(state: str) -> None:
    try:
        pyjwt.decode(state, settings.jwt_secret, algorithms=["HS256"])
    except pyjwt.PyJWTError:
        raise OAuthError("Ungültiger oder abgelaufener State-Parameter")


def redirect_uri(provider: str) -> str:
    return f"{settings.backend_url}/auth/oauth/{provider}/callback"


def build_authorize_url(provider: str, state: str) -> str:
    if provider == "apple":
        return _apple_authorize_url(state)
    if provider not in _STANDARD:
        raise OAuthError(f"Unbekannter Anbieter: {provider}")

    cfg = _STANDARD[provider]
    params = {
        "client_id": getattr(settings, f"{provider}_oauth_client_id"),
        "redirect_uri": redirect_uri(provider),
        "response_type": "code",
        "scope": cfg["scope"],
        "state": state,
        **cfg["auth_extra"],
    }
    return f"{cfg['auth_url']}?{urlencode(params)}"


async def fetch_user_info(provider: str, code: str) -> OAuthUserInfo:
    if provider == "apple":
        return await _apple_fetch_user_info(code)
    if provider not in _STANDARD:
        raise OAuthError(f"Unbekannter Anbieter: {provider}")

    cfg = _STANDARD[provider]
    client_id = getattr(settings, f"{provider}_oauth_client_id")
    client_secret = getattr(settings, f"{provider}_oauth_client_secret")

    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.post(
            cfg["token_url"],
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri(provider),
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
        if token_resp.status_code != 200:
            raise OAuthError(f"Token-Austausch fehlgeschlagen ({provider}): {token_resp.text[:200]}")

        access_token = token_resp.json().get("access_token")
        if not access_token:
            raise OAuthError(f"Kein Access-Token von {provider} erhalten")

        if provider == "facebook":
            info_resp = await client.get(
                cfg["userinfo_url"], params={"fields": "id,name,email", "access_token": access_token}
            )
        else:
            info_resp = await client.get(
                cfg["userinfo_url"], headers={"Authorization": f"Bearer {access_token}"}
            )
        if info_resp.status_code != 200:
            raise OAuthError(f"Profil-Abruf fehlgeschlagen ({provider}): {info_resp.text[:200]}")
        info = info_resp.json()

        if provider == "google":
            return OAuthUserInfo(provider_user_id=info["sub"], email=info.get("email"), name=info.get("name"))
        if provider == "microsoft":
            return OAuthUserInfo(
                provider_user_id=info["sub"],
                email=info.get("email") or info.get("preferred_username"),
                name=info.get("name"),
            )
        if provider == "facebook":
            return OAuthUserInfo(provider_user_id=info["id"], email=info.get("email"), name=info.get("name"))
        if provider == "github":
            email = info.get("email") or await _github_primary_email(client, access_token)
            return OAuthUserInfo(
                provider_user_id=str(info["id"]), email=email, name=info.get("name") or info.get("login")
            )

    raise OAuthError(f"Unbekannter Anbieter: {provider}")


async def _github_primary_email(client: httpx.AsyncClient, access_token: str) -> str | None:
    resp = await client.get(
        "https://api.github.com/user/emails", headers={"Authorization": f"Bearer {access_token}"}
    )
    if resp.status_code != 200:
        return None
    emails = resp.json()
    primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
    if primary:
        return primary["email"]
    verified = next((e for e in emails if e.get("verified")), None)
    return verified["email"] if verified else None


# --- Apple ("Sign in with Apple") ---

def _apple_client_secret() -> str:
    now = int(time.time())
    payload = {
        "iss": settings.apple_oauth_team_id,
        "iat": now,
        "exp": now + 300,
        "aud": "https://appleid.apple.com",
        "sub": settings.apple_oauth_client_id,
    }
    private_key = settings.apple_oauth_private_key.replace("\\n", "\n")
    return pyjwt.encode(payload, private_key, algorithm="ES256", headers={"kid": settings.apple_oauth_key_id})


def _apple_authorize_url(state: str) -> str:
    params = {
        "client_id": settings.apple_oauth_client_id,
        "redirect_uri": redirect_uri("apple"),
        "response_type": "code",
        "scope": "name email",
        "response_mode": "form_post",
        "state": state,
    }
    return f"https://appleid.apple.com/auth/authorize?{urlencode(params)}"


_apple_jwks_client: pyjwt.PyJWKClient | None = None


def _get_apple_jwks_client() -> pyjwt.PyJWKClient:
    global _apple_jwks_client
    if _apple_jwks_client is None:
        _apple_jwks_client = pyjwt.PyJWKClient("https://appleid.apple.com/auth/keys")
    return _apple_jwks_client


async def _apple_fetch_user_info(code: str) -> OAuthUserInfo:
    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.post(
            "https://appleid.apple.com/auth/token",
            data={
                "client_id": settings.apple_oauth_client_id,
                "client_secret": _apple_client_secret(),
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri("apple"),
            },
            headers={"Accept": "application/json"},
        )
    if token_resp.status_code != 200:
        raise OAuthError(f"Token-Austausch fehlgeschlagen (apple): {token_resp.text[:200]}")

    id_token = token_resp.json().get("id_token")
    if not id_token:
        raise OAuthError("Kein id_token von Apple erhalten")

    signing_key = _get_apple_jwks_client().get_signing_key_from_jwt(id_token)
    claims = pyjwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.apple_oauth_client_id,
        issuer="https://appleid.apple.com",
    )
    return OAuthUserInfo(provider_user_id=claims["sub"], email=claims.get("email"), name=None)
