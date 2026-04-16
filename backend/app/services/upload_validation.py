"""Единая валидация загрузок: magic bytes, безопасные имена и безопасное открытие изображений."""

from __future__ import annotations

import re
import zipfile
from io import BytesIO

from PIL import Image

# Сигнатуры для DOCX/RTF (RAG и шаблоны)
RTF_SIGNATURE = b"{\\rtf"
RTF_STRIP_PREFIX = b"\xef\xbb\xbf \t\r\n"
DOCX_REQUIRED_ENTRY = "word/document.xml"


# Сигнатуры по началу файла (magic bytes)
JPEG_SIG = b"\xff\xd8\xff"
PNG_SIG = b"\x89PNG\r\n\x1a\n"
GIF_SIG_GIF87A = b"GIF87a"
GIF_SIG_GIF89A = b"GIF89a"
PDF_SIG = b"%PDF"
WEBP_SIG = b"RIFF"  # первые 4 байта; байты 8:12 должны быть "WEBP"


def sanitize_filename_for_storage(raw: str | None, max_len: int = 120) -> str:
    """
    Санитизация имени файла для использования в ключе S3.
    Оставляет буквы (в т.ч. кириллица), цифры, точку, дефис, подчёркивание.
    Исключает path traversal и небезопасные символы.
    """
    if not raw or not (name := (raw or "").strip()):
        return "file"
    # Убираем путь, оставляем только последний компонент
    base = name.replace("\\", "/").split("/")[-1]
    safe = re.sub(r"[^0-9A-Za-z\u0400-\u04ff\u0451\u0401 _.-]+", "_", base).strip(" ._-")
    safe = (safe[:max_len] or "file").replace(" ", "_")
    return safe or "file"


def _is_jpeg(content: bytes) -> bool:
    return len(content) >= 3 and content[:3] == JPEG_SIG


def _is_png(content: bytes) -> bool:
    return len(content) >= 8 and content[:8] == PNG_SIG


def _is_gif(content: bytes) -> bool:
    return len(content) >= 6 and (content[:6] == GIF_SIG_GIF87A or content[:6] == GIF_SIG_GIF89A)


def _is_webp(content: bytes) -> bool:
    return len(content) >= 12 and content[:4] == WEBP_SIG and content[8:12] == b"WEBP"


def _is_pdf(content: bytes) -> bool:
    return len(content) >= 4 and content[:4] == PDF_SIG


def validate_image_signature(content: bytes) -> tuple[bool, str]:
    """
    Проверка, что содержимое соответствует одному из форматов изображения (JPEG, PNG, GIF, WebP).
    Возвращает (True, "") при успехе, (False, "сообщение об ошибке") при несовпадении.
    """
    if not content:
        return False, "Файл пустой"
    if _is_jpeg(content) or _is_png(content) or _is_gif(content) or _is_webp(content):
        return True, ""
    return False, "Содержимое файла не является изображением (ожидается JPEG, PNG, GIF или WebP)"


def validate_pdf_signature(content: bytes) -> tuple[bool, str]:
    """Проверка сигнатуры PDF. Возвращает (True, "") или (False, сообщение)."""
    if not content:
        return False, "Файл пустой"
    if _is_pdf(content):
        return True, ""
    return False, "Содержимое файла не является PDF"


# Лимит пикселей для защиты от decompression bomb (примерно 25 Мп)
MAX_IMAGE_PIXELS = 25_000_000


def safe_open_image(content: bytes) -> tuple[Image.Image | None, str]:
    """
    Безопасно открыть изображение: проверка целостности (verify), лимит пикселей, принудительная
    загрузка (load). Возвращает (PIL.Image, "") при успехе или (None, "сообщение об ошибке").
    """
    if not content:
        return None, "Файл пустой"
    old_max = getattr(Image, "MAX_IMAGE_PIXELS", None)
    try:
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
        img = Image.open(BytesIO(content))
        img.verify()
    except Exception as e:
        return None, f"Повреждённое или недопустимое изображение: {e!s}"
    finally:
        if old_max is not None:
            Image.MAX_IMAGE_PIXELS = old_max
    # verify() закрывает файл; открываем заново для load()
    try:
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
        img = Image.open(BytesIO(content))
        img.load()
        return img, ""
    except Exception as e:
        return None, f"Не удалось обработать изображение: {e!s}"
    finally:
        if old_max is not None:
            Image.MAX_IMAGE_PIXELS = old_max


def validate_image_or_pdf_signature(content: bytes, content_type: str) -> tuple[bool, str]:
    """
    Проверка по заявленному content_type: image/* — по сигнатуре изображения, application/pdf — PDF.
    Возвращает (True, "") или (False, сообщение).
    """
    ct = (content_type or "").strip().lower()
    if ct == "application/pdf":
        return validate_pdf_signature(content)
    if ct.startswith("image/"):
        return validate_image_signature(content)
    return False, "Неподдерживаемый тип файла для проверки сигнатуры"


def _is_valid_docx_content(content: bytes) -> bool:
    """Проверка, что содержимое — валидный DOCX (ZIP с word/document.xml)."""
    if len(content) < 4:
        return False
    try:
        with zipfile.ZipFile(BytesIO(content), "r") as zf:
            return DOCX_REQUIRED_ENTRY in zf.namelist()
    except (zipfile.BadZipFile, OSError):
        return False


def _detect_docx_rtf(content: bytes) -> str | None:
    """Возвращает 'rtf' или 'docx' по сигнатуре, иначе None."""
    if len(content) < 4:
        return None
    stripped = content.lstrip(RTF_STRIP_PREFIX)
    if stripped.startswith(RTF_SIGNATURE):
        return "rtf"
    if _is_valid_docx_content(content):
        return "docx"
    return None


def validate_rag_document(content: bytes, filename: str) -> tuple[str, str]:
    """
    Валидация документа для RAG: DOCX/RTF по сигнатурам, TXT — по UTF-8.
    Возвращает (document_type, ""), если всё ок, или ("", "единое сообщение об ошибке").
    """
    if not content:
        return "", "Файл пустой"
    name = (filename or "").strip().lower()
    if name.endswith(".docx"):
        claimed = "docx"
    elif name.endswith(".rtf"):
        claimed = "rtf"
    elif name.endswith(".txt"):
        claimed = "txt"
    else:
        return "", "Поддерживаются только файлы DOCX, TXT и RTF"

    if claimed == "txt":
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            return "", "Файл TXT должен быть в кодировке UTF-8"
        return "txt", ""

    detected = _detect_docx_rtf(content)
    if detected is None:
        return "", "Неверный формат файла: содержимое не соответствует DOCX или RTF"
    if detected != claimed:
        return "", "Расширение файла не совпадает с содержимым"
    return detected, ""
