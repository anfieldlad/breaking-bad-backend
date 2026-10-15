"""Unit tests for MongoDocumentRepository using a mocked driver."""

from unittest.mock import MagicMock

import pytest

from app.core.exceptions import DatabaseConnectionError, VectorSearchError
from app.models.document import Document
from app.repositories.document_repository import MongoDocumentRepository


@pytest.fixture
def collection():
    return MagicMock()


@pytest.fixture
def repo(settings, collection):
    client = MagicMock()
    client.__getitem__.return_value.__getitem__.return_value = collection
    return MongoDocumentRepository(settings, client=client)


def _doc(chunk_id=0):
    return Document(text="t", embedding=[0.1], filename="a.pdf", chunk_id=chunk_id)


def test_replace_file_inserts_before_deleting_old_version(repo, collection):
    collection.insert_many.return_value.inserted_ids = [1, 2]

    assert repo.replace_file("a.pdf", [_doc(0), _doc(1)]) == 2

    inserted = collection.insert_many.call_args.args[0]
    ingest_id = inserted[0]["ingest_id"]
    assert {d["ingest_id"] for d in inserted} == {ingest_id}
    collection.delete_many.assert_called_once_with(
        {"filename": "a.pdf", "ingest_id": {"$ne": ingest_id}}
    )
    assert [c[0] for c in collection.method_calls[:2]] == ["insert_many", "delete_many"]


def test_failed_insert_keeps_previous_version(repo, collection):
    collection.insert_many.side_effect = RuntimeError("write failed")

    with pytest.raises(DatabaseConnectionError):
        repo.replace_file("a.pdf", [_doc()])

    collection.delete_many.assert_not_called()


def test_vector_search_projects_out_embeddings(repo, collection):
    collection.aggregate.return_value = [
        {"_id": "x", "text": "t", "filename": "a.pdf", "chunk_id": 0, "score": 0.9}
    ]

    [doc] = repo.vector_search([0.1], limit=3)

    pipeline = collection.aggregate.call_args.args[0]
    assert "embedding" not in pipeline[1]["$project"]
    assert doc.score == 0.9 and doc.filename == "a.pdf"


def test_driver_errors_become_generic_app_errors(repo, collection):
    collection.aggregate.side_effect = RuntimeError("auth failed for mongodb://user:pw@host")

    with pytest.raises(VectorSearchError) as exc_info:
        repo.vector_search([0.1])

    assert "mongodb://" not in exc_info.value.detail
