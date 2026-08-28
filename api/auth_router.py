"""Auth Endpoints: Register, Login, Profile."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from auth.dependencies import get_current_user
from auth.security import create_access_token, hash_password, verify_password
from core.database import get_db
from core.models import Subscription, User

router = APIRouter(tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="E-Mail bereits registriert")

    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Passwort muss mindestens 8 Zeichen haben")

    user = User(email=req.email, password_hash=hash_password(req.password))
    db.add(user)
    db.flush()

    # Jeder User startet mit einem Free-Plan
    sub = Subscription(user_id=user.id, plan="free", status="active")
    db.add(sub)
    db.commit()

    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="E-Mail oder Passwort falsch")
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-Mail oder Passwort falsch")

    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return UserResponse(
        id=user.id,
        email=user.email,
        is_admin=user.is_admin,
        created_at=user.created_at,
        plan=user.subscription.plan if user.subscription else "free",
        modules=[m.module_name for m in user.modules],
    )
