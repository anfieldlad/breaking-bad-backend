"""Unit tests for health checks, request IDs and logging."""

import json
import logging

from app.core.logging import JsonFormatter, RequestIdFilter, request_id_var


def test_liveness(client):
    assert client.get("/health").json() == {"status": "awake"}


def test_readiness_reports_database_state(client, repository, monkeypatch):
    assert client.get("/health/ready").json() == {"status": "ready"}

    monkeypatch.setattr(repository, "ping", lambda: False)
    resp = client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json() == {"status": "unavailable"}


def test_response_carries_generated_request_id(client):
    resp = client.get("/health")
    assert len(resp.headers["X-Request-ID"]) == 32


def test_well_formed_incoming_request_id_is_reused(client):
    resp = client.get("/health", headers={"X-Request-ID": "trace-123"})
    assert resp.headers["X-Request-ID"] == "trace-123"


def test_malformed_incoming_request_id_is_replaced(client):
    resp = client.get("/health", headers={"X-Request-ID": "has spaces;and=junk"})
    assert resp.headers["X-Request-ID"] != "has spaces;and=junk"


def test_json_formatter_includes_request_id_and_extras():
    record = logging.makeLogRecord(
        {"name": "t", "levelname": "INFO", "msg": "hello %s", "args": ("world",), "chunks": 3}
    )
    token = request_id_var.set("req-1")
    try:
        RequestIdFilter().filter(record)
    finally:
        request_id_var.reset(token)

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "hello world"
    assert payload["request_id"] == "req-1"
    assert payload["chunks"] == 3
