from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "repops"
    environment: str = "development"
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+psycopg://repops:repops@localhost:5432/repops"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Analysis thresholds
    hate_speech_threshold: float = Field(default=0.6, ge=0.0, le=1.0)

    # Alerting
    slack_webhook_url: SecretStr | None = None
    alert_email: str = ""
    smtp_host: str = "localhost"
    smtp_port: int = 587

    # Observability
    prometheus_port: int = 9091        # API process
    prometheus_worker_port: int = 9092  # worker process
    log_file: str = ""  # override via LOG_FILE env var; empty = auto-detect

    # Apify
    apify_token: str = ""

    # Admin UI
    admin_username: str = "repops"
    admin_password: SecretStr = SecretStr("changeme")

    # Celery
    celery_timezone: str = "UTC"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
