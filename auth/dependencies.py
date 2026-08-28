"""FastAPI Dependencies für Auth."""

import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from auth.security import decode_access_token
from core.database import get_db
from core.models import User

_bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Extrahiert den User aus dem JWT-Token."""
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (pyjwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ungültig")

    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User nicht gefunden")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Nur Admins dürfen zugreifen."""
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin-Zugriff erforderlich")
    return user
