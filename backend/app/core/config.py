"""Application settings, read from environment variables (and an optional ``.env`` file).

Implemented with plain pydantic so the settings layer has no extra dependency.
"""
import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

_INSECURE_DEFAULT = "change-me-in-production-use-openssl-rand-hex-32"


class Settings(BaseModel):
    app_name: str = "Smart Code Plagiarism Detection System"
    environment: str = "development"  # development | production | test
    secret_key: str = _INSECURE_DEFAULT
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    database_url: str = "sqlite:///./dev.db"
    redis_url: str = "redis://localhost:6379/0"
    use_celery: bool = False  # False -> FastAPI BackgroundTasks (no Redis needed for local dev)

    cors_origins: str = "http://localhost:5173"
    storage_dir: Path = Path("./storage")
    max_upload_bytes: int = 2 * 1024 * 1024  # per file
    max_zip_bytes: int = 10 * 1024 * 1024
    max_zip_files: int = 100
    max_zip_uncompressed_bytes: int = 20 * 1024 * 1024
    max_submission_files: int = 50

    rate_limit_per_minute: int = 120
    auth_rate_limit_per_minute: int = 10

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-reply@example.com"
    frontend_url: str = "http://localhost:5173"
    password_reset_minutes: int = 30

    seed_admin_email: str = "admin@example.com"
    seed_admin_password: str = ""  # must be provided via env to create the first admin
    seed_demo_data: bool = False

    # Faculty may self-register only when they present this code (set FACULTY_REGISTRATION_CODE in the environment).
    # Empty (the default) disables faculty self-registration; an administrator can still create faculty accounts.
    faculty_registration_code: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def validate_for_runtime(self) -> None:
        if self.is_production and (self.secret_key == _INSECURE_DEFAULT or len(self.secret_key) < 32):
            raise RuntimeError("SECRET_KEY must be a random value of at least 32 characters in production")


def _read_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip().lower()] = val.strip().strip('"').strip("'")
    return values


@lru_cache
def get_settings() -> Settings:
    data = _read_dotenv(Path(".env"))
    if os.environ.get("APP_ENV") and not os.environ.get("ENVIRONMENT"):
        data["environment"] = os.environ["APP_ENV"]
    for name in Settings.model_fields:
        env = os.environ.get(name.upper())
        if env is not None:
            data[name] = env
    return Settings(**{k: v for k, v in data.items() if k in Settings.model_fields})
