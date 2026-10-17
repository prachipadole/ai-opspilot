"""
AI-OpsPilot – Application Configuration
All settings are read from environment variables (or .env).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "AI-OpsPilot"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"

    # ── API ───────────────────────────────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    api_prefix: str = "/api/v1"

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://opspilot:opspilot@localhost:5432/opspilot"
    sync_database_url: str = "postgresql://opspilot:opspilot@localhost:5432/opspilot"

    # ── Ollama ────────────────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # ── ChromaDB ──────────────────────────────────────────────────────────────
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "runbooks"

    # ── Anomaly Detection ─────────────────────────────────────────────────────
    anomaly_contamination: float = 0.05
    anomaly_window_seconds: int = 300

    # ── Frontend ──────────────────────────────────────────────────────────────
    streamlit_backend_url: str = "http://localhost:8000"


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
