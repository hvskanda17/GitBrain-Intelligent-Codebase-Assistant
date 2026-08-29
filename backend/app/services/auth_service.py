from datetime import datetime, timezone
from uuid import UUID

from app.core.exceptions import AlreadyExistsError, InvalidCredentialsError, TokenError
from app.core.redis import redis_client
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenPair, UserRegister

REVOKED_KEY_PREFIX = "revoked_jti:"


class AuthService:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def register(self, data: UserRegister) -> User:
        existing = await self.user_repo.get_by_email(data.email)
        if existing is not None:
            raise AlreadyExistsError(f"an account with email {data.email} already exists")
        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
        )
        return await self.user_repo.add(user)

    async def login(self, email: str, password: str) -> tuple[User, TokenPair]:
        user = await self.user_repo.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("incorrect email or password")
        if not user.is_active:
            raise InvalidCredentialsError("this account has been deactivated")
        return user, self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except Exception as exc:
            raise TokenError("refresh token is invalid or expired") from exc

        if await redis_client.exists(REVOKED_KEY_PREFIX + payload["jti"]):
            raise TokenError("refresh token has been revoked")

        user = await self.user_repo.get(UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise TokenError("refresh token no longer maps to an active user")

        # Rotate: the old refresh token dies the instant a new one is issued, so a
        # stolen-but-unused token is only ever good for one refresh.
        await self._revoke(payload["jti"], payload["exp"])
        return self._issue_tokens(user)

    async def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except Exception:
            return  # already invalid/expired -- logout is idempotent, not an error
        await self._revoke(payload["jti"], payload["exp"])

    async def _revoke(self, jti: str, exp: int) -> None:
        ttl_seconds = max(int(exp - datetime.now(timezone.utc).timestamp()), 1)
        await redis_client.set(REVOKED_KEY_PREFIX + jti, "1", ex=ttl_seconds)

    def _issue_tokens(self, user: User) -> TokenPair:
        return TokenPair(
            access_token=create_access_token(user.id, role=user.role.value),
            refresh_token=create_refresh_token(user.id),
        )
