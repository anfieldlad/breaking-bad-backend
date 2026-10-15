"""Unit tests for the document count/cleanup endpoints."""

from app.models.document import Document
from tests.unit.conftest import CLEANUP_PASSWORD


def _seed(repository, *filenames):
    repository.insert_many(
        [
            Document(text="t", embedding=[0.0], filename=name, chunk_id=i)
            for i, name in enumerate(filenames)
        ]
    )


def test_count(client, auth, repository):
    _seed(repository, "a.pdf", "b.pdf")
    resp = client.get("/api/documents/count", headers=auth)
    assert resp.status_code == 200
    assert resp.json() == {"count": 2}


def test_cleanup_rejects_wrong_password(client, auth, repository):
    _seed(repository, "a.pdf")
    resp = client.delete(
        "/api/documents?all=true", headers={**auth, "X-Cleanup-Password": "nope"}
    )
    assert resp.status_code == 403
    assert repository.count_documents() == 1


def test_cleanup_rejects_missing_password(client, auth, repository):
    _seed(repository, "a.pdf")
    resp = client.delete("/api/documents?all=true", headers=auth)
    assert resp.status_code == 403
    assert repository.count_documents() == 1


def test_cleanup_disabled_without_configured_password(client, auth, settings, repository):
    _seed(repository, "a.pdf")
    settings.cleanup_password = ""
    resp = client.delete(
        "/api/documents?all=true", headers={**auth, "X-Cleanup-Password": ""}
    )
    assert resp.status_code == 403
    assert "disabled" in resp.json()["detail"]
    assert repository.count_documents() == 1


def test_cleanup_by_filename(client, auth, repository):
    _seed(repository, "a.pdf", "b.pdf")
    resp = client.delete(
        "/api/documents?filename=a.pdf",
        headers={**auth, "X-Cleanup-Password": CLEANUP_PASSWORD},
    )
    assert resp.status_code == 200
    assert resp.json()["deleted_count"] == 1
    assert [d.filename for d in repository.documents] == ["b.pdf"]


def test_cleanup_all(client, auth, repository):
    _seed(repository, "a.pdf", "b.pdf")
    resp = client.delete(
        "/api/documents?all=true",
        headers={**auth, "X-Cleanup-Password": CLEANUP_PASSWORD},
    )
    assert resp.status_code == 200
    assert resp.json()["deleted_count"] == 2
