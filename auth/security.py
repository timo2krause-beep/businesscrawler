"""Passwort-Hashing und JWT-Token-Handling."""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from config.settings import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Dekodiert den Token. Wirft jwt.PyJWTError bei ungültigem Token."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
