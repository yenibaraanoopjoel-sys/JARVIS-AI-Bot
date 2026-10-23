"""Validated configuration for JARVIS; secrets are loaded from environment only."""
from functools import lru_cache
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JARVIS_", env_file=".env", extra="ignore")

    name: str = "JARVIS"
    owner_name: str = "Boss"
    log_level: str = "INFO"
    database_url: str = "sqlite:///data/jarvis.db"
    tts_enabled: bool = True
    stt_language: str = "en-US"
    wake_word_enabled: bool = False
    camera_enabled: bool = False
    allow_app_launch: bool = False
    allow_filesystem_writes: bool = False
    allow_terminal: bool = False
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", validation_alias="OPENAI_MODEL")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("JARVIS_LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
        return normalized

    @property
    def data_dir(self) -> Path:
        return Path("data")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
