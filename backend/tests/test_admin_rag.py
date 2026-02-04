"""Tests for admin RAG endpoints: upload documents (DOCX/TXT only), filename sanitization."""
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_upload_document_rejects_pdf(client, admin_headers):
    """POST /admin/documents с файлом .pdf возвращает 400."""
    response = await client.post(
        "/api/v1/admin/documents",
        headers=admin_headers,
        files={"file": ("price.pdf", b"%PDF-1.4 fake pdf content", "application/pdf")},
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "DOCX" in data["detail"] or "TXT" in data["detail"]


@pytest.mark.asyncio
async def test_upload_document_accepts_txt_and_calls_index_with_sanitized_name(client, admin_headers):
    """POST с .txt принимается; имя файла с путём санитизируется до последнего сегмента."""
    with patch("app.api.v1.routes.admin.index_document", new_callable=AsyncMock) as mock_index:
        mock_index.return_value = 2
        response = await client.post(
            "/api/v1/admin/documents",
            headers=admin_headers,
            files={"file": ("folder/sub/doc.txt", "Прайс услуг.\n\nТекст.".encode("utf-8"), "text/plain")},
        )
    assert response.status_code == 200
    data = response.json()
    assert data.get("chunks_added") == 2
    assert data.get("source_file") == "doc.txt"
    mock_index.assert_called_once()
    call_kwargs = mock_index.call_args
    assert call_kwargs[0][1] == "doc.txt"
    assert call_kwargs[0][3] == "txt"


@pytest.mark.asyncio
async def test_upload_document_accepts_docx(client, admin_headers):
    """POST с .docx принимается, index_document вызывается с document_type docx."""
    from io import BytesIO
    from docx import Document
    doc = Document()
    doc.add_paragraph("Тест RAG.")
    buf = BytesIO()
    doc.save(buf)
    content = buf.getvalue()
    with patch("app.api.v1.routes.admin.index_document", new_callable=AsyncMock) as mock_index:
        mock_index.return_value = 1
        response = await client.post(
            "/api/v1/admin/documents",
            headers=admin_headers,
            files={"file": ("rag.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
    assert response.status_code == 200
    assert response.json().get("source_file") == "rag.docx"
    mock_index.assert_called_once()
    assert mock_index.call_args[0][3] == "docx"


@pytest.mark.asyncio
async def test_upload_document_accepts_rtf(client, admin_headers):
    """POST с .rtf принимается, index_document вызывается с document_type rtf."""
    rtf_content = b"{\\rtf1\\ansi Hello from RTF}"
    with patch("app.api.v1.routes.admin.index_document", new_callable=AsyncMock) as mock_index:
        mock_index.return_value = 1
        response = await client.post(
            "/api/v1/admin/documents",
            headers=admin_headers,
            files={"file": ("doc.rtf", rtf_content, "application/rtf")},
        )
    assert response.status_code == 200
    assert response.json().get("source_file") == "doc.rtf"
    mock_index.assert_called_once()
    assert mock_index.call_args[0][3] == "rtf"


@pytest.mark.asyncio
async def test_upload_document_rejects_wrong_extension(client, admin_headers):
    """POST с расширением не .docx/.txt/.rtf возвращает 400."""
    response = await client.post(
        "/api/v1/admin/documents",
        headers=admin_headers,
        files={"file": ("data.csv", b"a,b,c", "text/csv")},
    )
    assert response.status_code == 400
    detail = response.json().get("detail", "")
    assert "DOCX" in detail or "TXT" in detail or "RTF" in detail


@pytest.mark.asyncio
async def test_upload_document_path_traversal_sanitized(client, admin_headers):
    """Имя файла вида path/to/file.txt сохраняется как file.txt."""
    with patch("app.api.v1.routes.admin.index_document", new_callable=AsyncMock) as mock_index:
        mock_index.return_value = 0
        response = await client.post(
            "/api/v1/admin/documents",
            headers=admin_headers,
            files={"file": ("../../etc/passwd.txt", b"", "text/plain")},
        )
    assert response.status_code == 200
    assert response.json().get("source_file") == "passwd.txt"
    mock_index.assert_called_once()
    assert mock_index.call_args[0][1] == "passwd.txt"


@pytest.mark.asyncio
async def test_upload_document_txt_invalid_utf8_returns_400(client, admin_headers):
    """TXT в не-UTF-8 кодировке возвращает 400 с сообщением про UTF-8."""
    with patch("app.api.v1.routes.admin.index_document", new_callable=AsyncMock) as mock_index:
        mock_index.side_effect = ValueError("Файл должен быть в кодировке UTF-8")
        response = await client.post(
            "/api/v1/admin/documents",
            headers=admin_headers,
            files={"file": ("bad.txt", b"\xff\xfe not utf8", "text/plain")},
        )
    assert response.status_code == 400
    assert "UTF-8" in response.json().get("detail", "")


@pytest.mark.asyncio
async def test_upload_document_requires_admin(client, auth_headers):
    """POST /admin/documents без роли admin возвращает 403."""
    response = await client.post(
        "/api/v1/admin/documents",
        headers=auth_headers,
        files={"file": ("x.txt", b"text", "text/plain")},
    )
    assert response.status_code == 403
