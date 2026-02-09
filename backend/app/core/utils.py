"""Shared utilities."""
import os
import re

# Разрешённые MIME для загрузки изображений (по magic bytes).
ALLOWED_IMAGE_MIMES = frozenset({"image/jpeg", "image/png", "image/gif", "image/webp"})


def is_allowed_image_bytes(data: bytes) -> bool:
    """Проверить, что данные по magic bytes являются разрешённым изображением (jpeg/png/gif/webp).

    Args:
        data: Сырые байты файла (достаточно начала файла).

    Returns:
        True, если тип определён и входит в ALLOWED_IMAGE_MIMES.
    """
    try:
        import filetype  # noqa: PLC0415

        kind = filetype.guess(data)
        return kind is not None and kind.mime in ALLOWED_IMAGE_MIMES
    except Exception:
        return False


def sanitize_upload_filename(filename: str | None, default: str = "image") -> str:
    """Make filename safe for S3 key: basename, no path traversal, safe chars only, max length.

    Args:
        filename: Original filename from upload (may be None or contain path).
        default: Value to use when result would be empty.

    Returns:
        Sanitized string safe to use in object key.
    """
    if not filename or not isinstance(filename, str):
        return default
    name = os.path.basename(filename)
    name = name.replace("..", "")
    name = re.sub(r"[^\w.\-]", "_", name).strip("._-")[:200]
    return name if name else default
