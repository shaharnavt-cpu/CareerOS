"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Runtime settings for the CareerOS backend."""

    model_config = SettingsConfigDict(
        env_file=(REPOSITORY_ROOT / ".env", REPOSITORY_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://careeros:careeros@localhost:5432/careeros"
    database_echo: bool = False
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_connect_timeout_seconds: int = 3
    reasoning_provider: str = "openai-compatible"
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "your-provider-model"
    llm_timeout_seconds: float = 30.0
    application_writer_provider: str = "local-deterministic"
    application_writer_data_policy: str = "private"
    openai_api_key: str | None = None
    openai_application_writer_model: str = "gpt-5.6-terra"
    openai_application_review_model: str | None = None
    openai_application_enable_review_pass: bool = False
    openai_application_timeout_seconds: float = Field(default=120.0, gt=0, le=300)
    openai_application_max_output_tokens: int = Field(default=6000, ge=256, le=20_000)
    openai_application_max_input_characters: int = Field(
        default=80_000, ge=10_000, le=250_000
    )
    openai_application_max_selected_memories: int = Field(default=4, ge=2, le=4)
    openai_application_reasoning_effort: str = "medium"
    run_live_openai_tests: bool = False
    cors_origins: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings instance."""

    return Settings()
