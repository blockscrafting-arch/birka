"""File response helpers."""
from __future__ import annotations

import re
from urllib.parse import quote


def _sanitize_component(value: str, max_len: int = 80) -> str:
    """Sanitize filename component, keeping readable characters."""
    safe = re.sub(r"[^0-9A-Za-zА-Яа-яЁё _.-]+", "_", value).strip(" ._-")
    return safe[:max_len] or "файл"


def content_disposition(filename: str) -> str:
    """Build Content-Disposition with UTF-8 filename and ASCII fallback."""
    safe = _sanitize_component(filename)
    ascii_fallback = re.sub(r"[^0-9A-Za-z_.-]+", "_", safe) or "file"
    quoted = quote(safe, safe="")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quoted}"
