"""Global Application Settings."""

from __future__ import annotations

from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Inno Markaz AI Agent"
    APP_ENV: Literal["development", "production", "test"] = "development"
    LOG_LEVEL: str = "INFO"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # PostgreSQL Database
    # DATABASE_URL: str = "postgresql://postgres:postgres@127.0.0.1:5432/inno_markaz"

    DATABASE_URL: str = "postgresql://inno_readonly:password@127.0.0.1:5432/inno_markaz"


    # LLM Settings
    LLM_PROVIDER: Literal["ollama", "openrouter"] = "openrouter"
    LLM_MAX_TOKENS: int = 5000
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "gemma4:latest"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "openrouter/free"


settings = Settings()
