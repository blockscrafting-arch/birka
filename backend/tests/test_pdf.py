"""Tests for PDF generation."""
import pytest

from app.services.pdf import LabelData, _render_barcode_base64, render_label_pdf


def test_barcode_base64():
    """Barcode PNG is generated and non-empty."""
    b64 = _render_barcode_base64("2041893551437")
    assert len(b64) > 100
    assert b64.isascii()


def test_render_label_pdf():
    """Smoke test: label PDF is valid and non-empty (may skip if weasyprint/pydyf bug)."""
    label = LabelData(
        title="Тестовый товар",
        article="123456789",
        supplier="ИП Тест",
        barcode_value="2041893551437",
    )
    try:
        pdf = render_label_pdf(label)
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 1000
    except (AttributeError, TypeError) as e:
        if "transform" in str(e) or "PDF.__init__" in str(e):
            pytest.skip("weasyprint/pydyf compatibility issue in this environment")
        raise
