from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "GitBrain"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Database — e.g. postgresql+asyncpg://user:pass@host:5432/gitbrain
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Embeddings — consumed starting Phase 4/7, defined now so config has one home
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    EMBEDDING_API_KEY: str | None = None
    EMBEDDING_API_BASE_URL: str = "https://api.openai.com/v1"
    EMBEDDING_BATCH_SIZE: int = 100

    # Ingestion (Phase 4)
    REPO_STORAGE_PATH: str = "/data/repos"
    GIT_CLONE_TIMEOUT_SECONDS: int = 300
    GIT_ALLOWED_PROTOCOLS: str = "http:https"  # public repos only for now -- no credential flow yet

    # LLM (Phase 8)
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str | None = None
    LLM_API_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"


@lru_cache
def get_settings() -> Settings:
    return Settings()
