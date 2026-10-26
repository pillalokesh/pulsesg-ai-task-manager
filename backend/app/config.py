import os
from dataclasses import dataclass

DEFAULT_JWT_SECRET = "change-this-development-secret-to-a-long-value"


def normalize_database_url(value: str) -> str:
    if value.startswith("jdbc:postgresql://"):
        value = value.removeprefix("jdbc:")
    if value.startswith("postgresql://"):
        value = value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str = normalize_database_url(
        os.getenv(
            "DATABASE_URL",
            os.getenv("DB_URL", "postgresql://pulsesg:change-me@localhost:5432/pulsesg"),
        )
    )
    jwt_secret: str = os.getenv("JWT_SECRET", DEFAULT_JWT_SECRET)
    app_env: str = os.getenv("APP_ENV", "development").lower()
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost"
        ).split(",")
        if origin.strip()
    )
    context_path: str = os.getenv("APP_CONTEXT_PATH", "").rstrip("/")
    create_schema: bool = os.getenv("DB_CREATE_SCHEMA", "false").lower() == "true"


settings = Settings()
