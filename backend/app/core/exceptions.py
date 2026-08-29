from typing import Any


class GitBrainError(Exception):
    """Base class for all application-raised errors. Carries an HTTP-status-agnostic
    error code so the API layer can map it to a response without the exception itself
    knowing about FastAPI -- services and repositories can raise these without
    importing anything from app.api."""

    code: str = "internal_error"
    status_code: int = 500

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(GitBrainError):
    code = "not_found"
    status_code = 404


class AlreadyExistsError(GitBrainError):
    code = "already_exists"
    status_code = 409


class InvalidCredentialsError(GitBrainError):
    code = "invalid_credentials"
    status_code = 401


class TokenError(GitBrainError):
    code = "invalid_token"
    status_code = 401


class PermissionDeniedError(GitBrainError):
    code = "permission_denied"
    status_code = 403


class ValidationError(GitBrainError):
    code = "validation_error"
    status_code = 422


class ConfigurationError(GitBrainError):
    code = "configuration_error"
    status_code = 503
