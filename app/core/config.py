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
    api_key: str

    # Optional settings with defaults
    db_name: str = "rag_app"
    collection_name: str = "documents"

    # Master password required for destructive document cleanup.
    # When empty, the cleanup endpoint is not password-gated.
    cleanup_password: str = ""

    # ----- LLM provider selection -----
    # Each can be independently set to "gemini" or "openai".
    # "openai" works with any OpenAI-compatible endpoint (OpenAI, vLLM,
    # Ollama, LM Studio, Together, Groq, etc.) via OPENAI_BASE_URL.
    chat_provider: str = "gemini"
    embedding_provider: str = "gemini"

    # Gemini credentials (required when a provider is set to "gemini")
    gemini_api_key: str = ""

    # OpenAI-compatible credentials (required when a provider is set to "openai")
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

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

    # Model names (must match the selected provider).
    # Gemini examples: chat="gemini-2.5-flash-lite", embedding="gemini-embedding-001"
    # OpenAI examples: chat="gpt-4o-mini", embedding="text-embedding-3-small"
    embedding_model: str = "gemini-embedding-001"
    chat_model: str = "gemini-2.5-flash-lite"

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
