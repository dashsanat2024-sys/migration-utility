from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from migration_utility.auth.service import decode_token, get_user_by_id
from migration_utility.config import get_settings
from migration_utility.datastore.models import User
from migration_utility.api.deps import get_db_session

_bearer = HTTPBearer(auto_error=False)


def get_optional_user(
    db: Session = Depends(get_db_session),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User | None:
    settings = get_settings()
    if not settings.auth_enabled:
        return None
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        user = get_user_by_id(db, UUID(payload["sub"]))
        if not user or not user.active:
            return None
        return user
    except Exception:
        return None


def get_current_user(
    user: User | None = Depends(get_optional_user),
) -> User:
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Auth disabled — set AUTH_ENABLED=true",
        )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user
