"""Unit tests for the PDF ingestion endpoint."""

import io

import pytest
from pypdf import PdfWriter


def _pdf_bytes() -> bytes:
    """A one-page PDF with no extractable text."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.fixture
def text_pdf(monkeypatch):
    """Make text extraction return fixed text so blank PDFs count as content."""
    from pypdf import PageObject

    monkeypatch.setattr(PageObject, "extract_text", lambda self, *a, **k: "Page text")
    return _pdf_bytes()


def _upload(client, auth, name, data):
    return client.post(
        "/api/ingest",
        headers=auth,
        files={"file": (name, data, "application/pdf")},
    )


def test_ingest_stores_chunks(client, auth, repository, text_pdf):
    resp = _upload(client, auth, "doc.pdf", text_pdf)

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"message": "Success", "chunks_stored": 1}
    assert [d.filename for d in repository.documents] == ["doc.pdf"]


def test_reingesting_a_file_replaces_it(client, auth, repository, text_pdf):
    _upload(client, auth, "doc.pdf", text_pdf)
    _upload(client, auth, "doc.pdf", text_pdf)

    assert repository.count_documents() == 1


def test_rejects_non_pdf_extension(client, auth):
    resp = _upload(client, auth, "notes.txt", b"hello")
    assert resp.status_code == 400
    assert "not a PDF" in resp.json()["detail"]


def test_rejects_non_pdf_content_with_pdf_extension(client, auth):
    resp = _upload(client, auth, "fake.pdf", b"<html>not a pdf</html>")
    assert resp.status_code == 400
    assert "not a valid PDF" in resp.json()["detail"]


def test_rejects_pdf_without_text(client, auth):
    resp = _upload(client, auth, "blank.pdf", _pdf_bytes())
    assert resp.status_code == 400
    assert "no extractable text" in resp.json()["detail"]


def test_rejects_oversized_upload(client, auth, settings):
    settings.max_upload_mb = 1
    resp = _upload(client, auth, "big.pdf", b"%PDF-" + b"0" * (1024 * 1024))
    assert resp.status_code == 413


def test_corrupt_pdf_error_hides_parser_details(client, auth):
    resp = _upload(client, auth, "broken.pdf", b"%PDF-1.7 garbage that is not a pdf")
    assert resp.status_code == 400
    assert resp.json() == {"detail": "Failed to process PDF file"}
