"""Functional tests for ingestion + document cleanup endpoints."""

import pytest

from tests.conftest import TEST_PREFIX

pytestmark = pytest.mark.integration


def test_delete_requires_auth(client):
    resp = client.delete("/api/documents?all=true")
    assert resp.status_code == 401


def test_delete_requires_a_selector(client, cleanup_headers):
    resp = client.delete("/api/documents", headers=cleanup_headers)
    assert resp.status_code == 400


def test_delete_rejects_both_selectors(client, cleanup_headers):
    resp = client.delete(
        "/api/documents?all=true&filename=x.pdf", headers=cleanup_headers
    )
    assert resp.status_code == 400


def test_delete_rejects_wrong_password(client, auth, settings):
    if not settings.cleanup_password:
        pytest.skip("no cleanup password configured; password gate disabled")
    resp = client.delete(
        "/api/documents?all=true",
        headers={**auth, "X-Cleanup-Password": "definitely-wrong"},
    )
    assert resp.status_code == 403


def test_ingest_then_count(client, auth, ingest):
    filename, chunks = ingest("count", "alpha document")
    assert chunks >= 1

    resp = client.get("/api/documents/count", headers=auth)
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1


def test_delete_by_filename(client, cleanup_headers, mongo, ingest):
    filename, _ = ingest("byfile", "beta document")
    assert mongo.count_documents({"filename": filename}) >= 1

    resp = client.delete(
        f"/api/documents?filename={filename}", headers=cleanup_headers
    )
    assert resp.status_code == 200
    assert resp.json()["deleted_count"] >= 1
    assert mongo.count_documents({"filename": filename}) == 0


def test_delete_all_is_safe_with_real_data(client, auth, cleanup_headers, mongo, ingest):
    """`all=true` must wipe the collection — but never when real data exists."""
    real = mongo.count_documents(
        {"filename": {"$not": {"$regex": f"^{TEST_PREFIX}"}}}
    )
    if real > 0:
        pytest.skip(
            f"collection holds {real} non-test document(s); "
            "skipping destructive all=true test to protect real data"
        )

    ingest("wipe", "gamma document")
    resp = client.delete("/api/documents?all=true", headers=cleanup_headers)
    assert resp.status_code == 200
    assert client.get("/api/documents/count", headers=auth).json()["count"] == 0
