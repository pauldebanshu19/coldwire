"""Password hashing (bcrypt) + JWT issue/verify (PyJWT)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app_settings import get_app_settings

_s = get_app_settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=_s.jwt_expire_minutes),
    }
    return jwt.encode(payload, _s.jwt_secret, algorithm=_s.jwt_alg)


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, _s.jwt_secret, algorithms=[_s.jwt_alg])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
