"""Application configuration, loaded from environment variables."""

import warnings
from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULT = "change_me_in_production"


class Settings(BaseSettings):
    APP_NAME: str = "Meridian"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"   # development | staging | production
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = _INSECURE_DEFAULT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    ALGORITHM: str = "HS256"
    ALLOWED_ORIGINS: str = "http://localhost:5173"  # comma-separated

    # Database
    DATABASE_URL: str = "sqlite:///./meridian.db"

    # Redis / task queue
    REDIS_URL: str = "redis://localhost:6379/0"

    # OpenAI
    OPENAI_API_KEY: str = "sk-placeholder"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    CHAT_MODEL: str = "gpt-5.6-terra"    # Extraction, qualification, RAG answers
    FAST_MODEL: str = "gpt-5.6-luna"     # Cheaper/faster tier for lower-stakes generation (email drafts)

    # Vector store
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "meridian_docs"
    CHROMA_HOST: str | None = None
    CHROMA_PORT: int = Field(8001, ge=1, le=65535)

    # Document processing
    UPLOAD_DIR: str = "./uploads"
    CHUNK_SIZE: int = Field(800, gt=0)
    CHUNK_OVERLAP: int = Field(100, ge=0)
    MAX_UPLOAD_SIZE_MB: int = Field(20, gt=0)

    # RAG
    TOP_K_RESULTS: int = Field(5, ge=1, le=20)
    MIN_SIMILARITY_SCORE: float = Field(0.3, ge=0, le=1)

    # Rate limiting
    # "memory://" works out of the box for a single process. If you run more
    # than one API replica, point this at Redis (the same instance used for
    # Celery is fine) so limits are enforced consistently across replicas —
    # e.g. redis://localhost:6379/1
    RATE_LIMIT_STORAGE_URI: str = "memory://"
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_DEFAULT: str = "120/minute"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("ENVIRONMENT")
    @classmethod
    def _normalize_environment(cls, v: str) -> str:
        v = v.lower()
        if v not in {"development", "staging", "production"}:
            raise ValueError("ENVIRONMENT must be one of: development, staging, production")
        return v

    @model_validator(mode="after")
    def _validate_chunk_overlap(self):
        if self.CHUNK_OVERLAP >= self.CHUNK_SIZE:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        return self

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    def validate_production_readiness(self) -> None:
        """Refuse to boot with insecure defaults once ENVIRONMENT=production."""
        if not self.is_production:
            return
        problems = []
        if self.SECRET_KEY == _INSECURE_DEFAULT or len(self.SECRET_KEY) < 32:
            problems.append(
                "SECRET_KEY is missing or too weak. Generate one with: "
                "python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if not self.OPENAI_API_KEY.strip() or self.OPENAI_API_KEY == "sk-placeholder":
            problems.append("OPENAI_API_KEY is not set.")
        if "*" in self.cors_origins:
            problems.append("ALLOWED_ORIGINS must not be '*' in production.")
        if self.DATABASE_URL.startswith("sqlite"):
            warnings.warn(
                "Running production on SQLite. Postgres is strongly recommended "
                "for concurrent write throughput.",
                RuntimeWarning,
                stacklevel=2,
            )
        if problems:
            raise RuntimeError(
                "Refusing to start in production with insecure configuration:\n- "
                + "\n- ".join(problems)
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
