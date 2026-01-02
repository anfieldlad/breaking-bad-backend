"""
Application configuration using pydantic-settings.

Provides type-safe, validated configuration loaded from environment variables.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Required settings (no defaults - must be provided)
    mongo_uri: str
    gemini_api_key: str
    api_key: str

    # Optional settings with defaults
    db_name: str = "rag_app"
    collection_name: str = "documents"

    # Application settings
    app_name: str = "Breaking B.A.D. API"
    app_version: str = "1.0.0"
    debug: bool = False

    # PDF processing limits
    max_pages_per_pdf: int = 20

    # Vector search settings
    vector_index_name: str = "vector_index"
    vector_search_candidates: int = 50
    vector_search_limit: int = 5

    # Gemini model settings
    embedding_model: str = "text-embedding-004"
    chat_model: str = "gemini-2.0-flash"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are only loaded once,
    providing a singleton-like behavior for performance.
    """
    return Settings()
