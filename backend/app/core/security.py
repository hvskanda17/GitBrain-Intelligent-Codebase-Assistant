from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

import bcrypt
import jwt
from jwt import InvalidTokenError

from app.core.config import get_settings

settings = get_settings()


def hash_password(plain_password: str) -> str:
    """Bcrypt-hash a plaintext password. Truncates at 72 bytes (bcrypt's own limit)
    rather than silently corrupting longer inputs -- schemas.auth.UserRegister already
    caps input length, this is a second line of defense."""
    pwd_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8")[:72], hashed_password.encode("utf-8"))
    except ValueError:
        # malformed hash in the DB -- fail closed, never raise into the auth flow
        return False


def _create_token(
    subject: UUID,
    token_type: Literal["access", "refresh"],
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if token_type == "refresh":
        # lets a single refresh token be revoked/rotated without touching any other token
        payload["jti"] = str(uuid4())
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: UUID, role: str) -> str:
    return _create_token(
        user_id, "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims={"role": role},
    )


def create_refresh_token(user_id: UUID) -> str:
    return _create_token(user_id, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, expected_type: Literal["access", "refresh"]) -> dict[str, Any]:
    """Raises jwt.InvalidTokenError (or a subclass) on any failure -- expired, bad
    signature, wrong type. Callers convert that into a 401 at the API boundary; this
    module stays framework-agnostic."""
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != expected_type:
        raise InvalidTokenError(f"expected a {expected_type} token, got {payload.get('type')}")
    return payload
