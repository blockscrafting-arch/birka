"""Barcode generation."""
from io import BytesIO

import barcode
from barcode.writer import ImageWriter


def generate_code128(data: str) -> bytes:
    """Generate Code128 barcode image bytes."""
    code = barcode.get("code128", data, writer=ImageWriter())
    buffer = BytesIO()
    code.write(buffer, options={"module_height": 15.0, "module_width": 0.4})
    return buffer.getvalue()
