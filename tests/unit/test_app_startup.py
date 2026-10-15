"""Unit tests for application wiring and lifecycle."""

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import ConfigurationError
from app.main import create_app


def test_startup_builds_services_and_serves_health(settings):
    with TestClient(create_app(settings)) as client:
        assert client.app.state.services is not None
        assert client.get("/health").json() == {"status": "awake"}


def test_startup_fails_fast_on_missing_provider_key(settings):
    settings.gemini_api_key = ""
    with pytest.raises(ConfigurationError):
        with TestClient(create_app(settings)):
            pass


def test_provider_names_are_case_insensitive(settings):
    from app.core.config import Settings

    loaded = Settings(**{**settings.model_dump(), "chat_provider": "OpenAI"})
    assert loaded.chat_provider == "openai"


def test_unknown_provider_is_rejected_at_load_time(settings):
    import pytest
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(**{**settings.model_dump(), "chat_provider": "anthropic"})


def test_cors_disabled_by_default(settings):
    client = TestClient(create_app(settings))
    resp = client.options(
        "/api/chat",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in resp.headers


def test_cors_allows_configured_origin_only(settings):
    settings.cors_origins = "https://ui.example"
    client = TestClient(create_app(settings))

    allowed = client.options(
        "/api/chat",
        headers={"Origin": "https://ui.example", "Access-Control-Request-Method": "POST"},
    )
    denied = client.options(
        "/api/chat",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )

    assert allowed.headers["access-control-allow-origin"] == "https://ui.example"
    assert "access-control-allow-origin" not in denied.headers
