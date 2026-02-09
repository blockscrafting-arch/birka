"""Tests for upload validation: magic bytes, sanitize filename, safe image open."""
import pytest

from app.services.upload_validation import (
    sanitize_filename_for_storage,
    validate_image_signature,
    validate_pdf_signature,
    validate_rag_document,
    validate_image_or_pdf_signature,
    safe_open_image,
)


def test_sanitize_filename_for_storage_empty():
    assert sanitize_filename_for_storage("") == "file"
    assert sanitize_filename_for_storage(None) == "file"


def test_sanitize_filename_for_storage_strips_path():
    assert sanitize_filename_for_storage("folder/../name.docx") == "name.docx"
    assert ".." not in sanitize_filename_for_storage("../../etc/passwd")


def test_sanitize_filename_for_storage_replaces_unsafe():
    assert sanitize_filename_for_storage("a<b>c|.txt") == "a_b_c_.txt"
    assert sanitize_filename_for_storage("  x  ") == "x"


def test_validate_image_signature_jpeg():
    ok, err = validate_image_signature(b"\xff\xd8\xff\xe0\x00\x10JFIF")
    assert ok is True
    assert err == ""


def test_validate_image_signature_png():
    ok, err = validate_image_signature(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
    assert ok is True
    assert err == ""


def test_validate_image_signature_gif():
    ok, err = validate_image_signature(b"GIF89a\x01\x00\x01\x00")
    assert ok is True
    assert err == ""


def test_validate_image_signature_webp():
    ok, err = validate_image_signature(b"RIFF\x00\x00\x00\x00WEBP")
    assert ok is True
    assert err == ""


def test_validate_image_signature_rejects_wrong():
    ok, err = validate_image_signature(b"not an image")
    assert ok is False
    assert "изображением" in err or "JPEG" in err


def test_validate_pdf_signature():
    ok, err = validate_pdf_signature(b"%PDF-1.4 fake")
    assert ok is True
    assert err == ""
    ok2, err2 = validate_pdf_signature(b"not pdf")
    assert ok2 is False
    assert "PDF" in err2


def test_validate_image_or_pdf_signature():
    ok, _ = validate_image_or_pdf_signature(b"%PDF-1.4 x", "application/pdf")
    assert ok is True
    ok2, _ = validate_image_or_pdf_signature(b"\xff\xd8\xff", "image/jpeg")
    assert ok2 is True
    ok3, err3 = validate_image_or_pdf_signature(b"x", "application/pdf")
    assert ok3 is False
    assert "PDF" in err3


def test_validate_rag_document_txt_utf8():
    doc_type, err = validate_rag_document("Hello".encode("utf-8"), "doc.txt")
    assert doc_type == "txt"
    assert err == ""


def test_validate_rag_document_txt_invalid_utf8():
    doc_type, err = validate_rag_document(b"\xff\xfe not utf8", "f.txt")
    assert doc_type == ""
    assert "UTF-8" in err


def test_validate_rag_document_docx():
    from io import BytesIO
    import zipfile
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", "<w:document/>")
    content = buf.getvalue()
    doc_type, err = validate_rag_document(content, "file.docx")
    assert doc_type == "docx"
    assert err == ""


def test_validate_rag_document_docx_wrong_content_returns_error():
    doc_type, err = validate_rag_document(b"not a docx", "file.docx")
    assert doc_type == ""
    assert "Неверный" in err or "не соответствует" in err


def test_validate_rag_document_rtf():
    doc_type, err = validate_rag_document(b"{\\rtf1\\ansi hi}", "f.rtf")
    assert doc_type == "rtf"
    assert err == ""


def test_validate_rag_document_rejects_wrong_extension():
    doc_type, err = validate_rag_document(b"x", "file.csv")
    assert doc_type == ""
    assert "DOCX" in err or "TXT" in err or "RTF" in err


def test_safe_open_image_valid_jpeg():
    """Minimal valid 1x1 JPEG from Pillow passes safe_open_image."""
    from io import BytesIO
    from PIL import Image
    buf = BytesIO()
    Image.new("RGB", (1, 1), color="red").save(buf, format="JPEG")
    jpeg = buf.getvalue()
    img, err = safe_open_image(jpeg)
    assert img is not None
    assert err == ""
    img.close()


def test_safe_open_image_empty():
    img, err = safe_open_image(b"")
    assert img is None
    assert "пустой" in err or err


def test_safe_open_image_invalid_content():
    img, err = safe_open_image(b"\xff\xd8\xff truncated")
    assert img is None
    assert err != ""
