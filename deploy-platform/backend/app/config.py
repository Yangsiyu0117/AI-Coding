import os
from pathlib import Path

from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "Deploy Platform"
    app_version: str = "0.6.0"
    app_brand: str = ""
    app_title: str = "运维升级发布平台"
    debug: bool = True

    database_url: str = f"sqlite:///{BASE_DIR.parent / 'data' / 'deploy_platform.db'}"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    upload_dir: str = str(BASE_DIR / "uploads")
    log_dir: str = str(BASE_DIR.parent / "logs")
    max_upload_size_mb: int = 500
    allowed_upload_extensions: list[str] = [".tar.gz", ".zip", ".tgz", ".gz", ".bin"]

    remote_update_base: str = "/opt/deploy-platform/update"

    ssh_default_timeout: int = 10

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = {"env_prefix": "APP_", "env_file": ".env"}


settings = Settings()
