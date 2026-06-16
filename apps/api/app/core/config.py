import os
from dataclasses import dataclass, field
from pathlib import Path


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "My Daily Headlines API")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./daily_headlines.db")
    cors_origins: list[str] = field(
        default_factory=lambda: _split_csv(
            os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
        )
    )
    dev_admin_username: str = os.getenv("DEV_ADMIN_USERNAME", "admin")
    dev_admin_password: str = os.getenv("DEV_ADMIN_PASSWORD", "")
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = int(os.getenv("JWT_EXPIRE_HOURS", "72"))
    scheduler_enabled: bool = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"
    scheduler_interval_seconds: int = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "60"))
    uploads_dir: Path = field(
        default_factory=lambda: Path(os.getenv("UPLOADS_DIR", "./uploads")).resolve()
    )
    uploads_url_path: str = os.getenv("UPLOADS_URL_PATH", "/uploads")


settings = Settings()
