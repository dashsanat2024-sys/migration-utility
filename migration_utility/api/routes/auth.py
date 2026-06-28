from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from migration_utility.auth.deps import get_current_user
from migration_utility.auth.service import authenticate, create_access_token, ensure_seed_admin
from migration_utility.api.deps import get_db_session
from migration_utility.config import get_settings
from migration_utility.datastore.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)


class UserRead(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: str

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db_session)) -> LoginResponse:
    ensure_seed_admin(db)
    user = authenticate(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user)
    return LoginResponse(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/status")
def auth_status() -> dict:
    settings = get_settings()
    return {
        "auth_enabled": settings.auth_enabled,
        "runner_mode": settings.runner_mode,
        "async_runs_enabled": settings.async_runs_enabled,
    }


@router.get("/users", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> list[User]:
    return list(db.scalars(select(User).where(User.active.is_(True)).order_by(User.email)))
