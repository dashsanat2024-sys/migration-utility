from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from migration_utility.config import get_settings
from migration_utility.datastore.models import User

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, salt, digest = password_hash.split("$", 2)
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return secrets.compare_digest(check, digest)


def create_access_token(user: User) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.auth_token_hours)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "name": user.display_name,
        "exp": expire,
    }
    return jwt.encode(payload, settings.auth_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.auth_secret, algorithms=[ALGORITHM])


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email.lower().strip()))
    if not user or not user.active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_user_by_id(db: Session, user_id: UUID) -> User | None:
    return db.get(User, user_id)


def ensure_seed_admin(db: Session) -> None:
    settings = get_settings()
    existing = db.scalar(select(User).limit(1))
    if existing:
        return
    user = User(
        email=settings.auth_seed_email.lower(),
        display_name=settings.auth_seed_name,
        password_hash=hash_password(settings.auth_seed_password),
        role="product_owner",
        active=True,
    )
    db.add(user)
    db.commit()
