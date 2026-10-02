from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "CareerAI API"
    environment: Literal["development", "testing", "production"] = "development"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    database_url: str = "postgresql+psycopg://careerai:replace-with-a-local-password@localhost:5433/careerai_dev"
    test_database_url: str = "postgresql+psycopg://careerai_test:replace-with-a-local-password@localhost:5434/careerai_test"
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    max_upload_size_mb: int = 10
    upload_directory: Path = Path("var/resumes")
    allowed_resume_extensions: list[str] = [".pdf"]
    allowed_resume_content_types: list[str] = ["application/pdf"]
    llm_provider: Literal["disabled", "openai", "ollama"] = "disabled"
    llm_api_key: SecretStr | None = None
    llm_model: str = ""
    llm_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    llm_max_retries: int = Field(default=1, ge=0, le=1)
    llm_max_input_chars: int = Field(default=20_000, gt=0)

    @model_validator(mode="after")
    def validate_secret_key(self) -> "Settings":
        if self.environment == "production":
            if self.secret_key in {"change-me-in-production", "replace-with-a-real-secret", ""}:
                raise ValueError("SECRET_KEY must be set to a real secret in production.")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"