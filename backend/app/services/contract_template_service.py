"""Contract template service: file upload, PDF↔DOCX conversion, placeholder substitution, DOCX→PDF."""
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
import zipfile
from io import BytesIO

from app.core.config import settings
from app.core.logging import logger
from app.services.pdf import ContractData
from app.services.s3 import S3Service

# S3 prefix for contract template files
CONTRACT_TEMPLATE_PREFIX = "contract-templates/"
MAX_TEMPLATE_SIZE_BYTES = getattr(
    settings, "MAX_UPLOAD_SIZE_BYTES", 10 * 1024 * 1024
)  # 10 MB
ALLOWED_TEMPLATE_EXTENSIONS = (".docx", ".rtf")
CONTENT_TYPE_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
CONTENT_TYPE_RTF = "application/rtf"

# RTF signature: {\rtf (allow BOM/whitespace before)
RTF_SIGNATURE = b"{\\rtf"
RTF_STRIP_PREFIX = b"\xef\xbb\xbf \t\r\n"  # UTF-8 BOM + common whitespace
DOCX_REQUIRED_ENTRY = "word/document.xml"


def _sanitize_filename(name: str, max_len: int = 120) -> str:
    """Sanitize filename for S3 key: keep alphanumeric, dots, hyphen, underscore."""
    base = re.sub(r"[^0-9A-Za-zА-Яа-яЁё _.-]+", "_", (name or "").strip()).strip(" ._-")
    return (base[:max_len] or "file").replace(" ", "_")


def _strip_extension(filename: str, ext: str) -> str:
    """Remove extension from filename if it matches (case-insensitive)."""
    if not filename or not ext:
        return filename
    ext = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
    f = filename.lower()
    if f.endswith(ext):
        return filename[: -len(ext)]
    return filename


def _build_template_s3_key(base_name_no_ext: str, suffix: str) -> str:
    """Build unique S3 key. base_name_no_ext must not contain extension; suffix is e.g. .docx or .pdf."""
    safe = _sanitize_filename(base_name_no_ext)
    uid = uuid.uuid4().hex[:12]
    return f"{CONTRACT_TEMPLATE_PREFIX}{uid}_{safe}{suffix}"


def _is_valid_docx(content: bytes) -> bool:
    """Check that content is a valid DOCX (ZIP with word/document.xml)."""
    if len(content) < 4:
        return False
    try:
        with zipfile.ZipFile(BytesIO(content), "r") as zf:
            return DOCX_REQUIRED_ENTRY in zf.namelist()
    except (zipfile.BadZipFile, OSError):
        return False


def _detect_file_type_by_signature(content: bytes) -> str | None:
    """Return 'rtf' or 'docx' if content matches format, else None. RTF allows BOM/whitespace before {\\rtf."""
    if len(content) < 4:
        return None
    stripped = content.lstrip(RTF_STRIP_PREFIX)
    if stripped.startswith(RTF_SIGNATURE):
        return "rtf"
    if _is_valid_docx(content):
        return "docx"
    return None


def validate_template_upload(content: bytes, filename: str) -> tuple[str, str]:
    """
    Validate uploaded file for contract template (extension + magic bytes).
    Returns (file_type, error_message). file_type is 'docx' or 'rtf', error_message empty if valid.
    """
    if len(content) > MAX_TEMPLATE_SIZE_BYTES:
        return (
            "",
            f"Файл слишком большой. Максимум {MAX_TEMPLATE_SIZE_BYTES // (1024 * 1024)} MB",
        )
    name = (filename or "").strip().lower()
    if name.endswith(".docx"):
        claimed = "docx"
    elif name.endswith(".rtf"):
        claimed = "rtf"
    else:
        return "", "Поддерживаются только файлы DOCX и RTF"
    detected = _detect_file_type_by_signature(content)
    if detected is None:
        return "", "Неверный формат файла: содержимое не соответствует DOCX или RTF"
    if detected != claimed:
        return "", f"Расширение файла не совпадает с содержимым (ожидается {claimed})"
    return claimed, ""


def rtf_to_docx_bytes(rtf_bytes: bytes) -> bytes:
    """Convert RTF to DOCX using LibreOffice. Returns DOCX bytes. Logs stderr on failure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rtf_path = os.path.join(tmpdir, "template.rtf")
        with open(rtf_path, "wb") as f:
            f.write(rtf_bytes)
        cmd = _get_libreoffice_cmd()
        try:
            subprocess.run(
                [
                    cmd,
                    "--headless",
                    "--convert-to", "docx",
                    "--outdir", tmpdir,
                    rtf_path,
                ],
                check=True,
                capture_output=True,
                timeout=60,
                env={**os.environ, "HOME": tmpdir},
            )
        except subprocess.CalledProcessError as e:
            logger.exception(
                "contract_rtf_to_docx_failed",
                stderr=(e.stderr and e.stderr.decode(errors="replace")) or "",
                error=str(e),
            )
            raise
        except FileNotFoundError:
            logger.error("libreoffice_not_found", msg="LibreOffice not in PATH")
            raise RuntimeError("Конвертация RTF в DOCX недоступна: LibreOffice не найден") from None
        docx_path = os.path.join(tmpdir, "template.docx")
        if not os.path.isfile(docx_path):
            raise RuntimeError("LibreOffice не создал DOCX из RTF")
        with open(docx_path, "rb") as f:
            return f.read()


def upload_template_file(
    s3: S3Service,
    content: bytes,
    file_name: str,
    file_type: str,
) -> tuple[str, str | None]:
    """
    Upload template file to S3. Returns (file_key, docx_key). docx_key is None (only DOCX/RTF stored).
    On any upload failure, already-uploaded keys are not cleaned here; caller must call delete_template_files.
    """
    ext = ".rtf" if file_type == "rtf" else ".docx"
    base_no_ext = _strip_extension(file_name, ext)
    file_key = _build_template_s3_key(base_no_ext, ext)
    docx_key = None

    content_type = CONTENT_TYPE_RTF if file_type == "rtf" else CONTENT_TYPE_DOCX
    s3.upload_bytes(file_key, content, content_type)
    return file_key, docx_key


HEAD_CHECK_RETRIES = 3
HEAD_CHECK_BACKOFF_SEC = 0.15


async def head_check_upload(s3: S3Service, key: str) -> bool:
    """
    Verify uploaded file is reachable via public URL (HEAD).
    Retries up to HEAD_CHECK_RETRIES times with short backoff on failure.
    """
    import asyncio

    url = s3.build_public_url(key)
    for attempt in range(HEAD_CHECK_RETRIES):
        if await s3.head_check(url):
            return True
        if attempt < HEAD_CHECK_RETRIES - 1:
            await asyncio.sleep(HEAD_CHECK_BACKOFF_SEC)
    logger.warning("contract_template_head_check_failed_after_retries", key=key)
    return False


def get_docx_bytes_for_template(s3: S3Service, file_key: str, file_type: str, docx_key: str | None) -> bytes:
    """
    Return DOCX bytes for a template: from docx_key if legacy PDF; from file_key if DOCX;
    if RTF, convert to DOCX on the fly. Legacy PDF without docx_key raises RuntimeError.
    """
    ft = (file_type or "").lower()
    if ft == "pdf":
        if docx_key:
            return s3.get_bytes(docx_key)
        logger.warning(
            "contract_template_pdf_without_docx",
            file_key=file_key,
            msg="Legacy PDF template has no converted DOCX",
        )
        raise RuntimeError(
            "Старый шаблон в формате PDF без конвертированной копии. Загрузите шаблон заново в формате DOCX или RTF."
        )
    raw = s3.get_bytes(file_key)
    if ft == "rtf":
        return rtf_to_docx_bytes(raw)
    return raw


def render_docx_with_context(docx_bytes: bytes, context: dict[str, str]) -> bytes:
    """
    Apply placeholder substitution in DOCX using docxtpl (Jinja2-style {{ key }}).
    Returns rendered DOCX bytes.
    """
    from docxtpl import DocxTemplate

    doc = DocxTemplate(BytesIO(docx_bytes))
    # docxtpl expects string values; ensure no None
    safe_ctx = {k: (v if v is not None else "-") for k, v in context.items()}
    doc.render(safe_ctx)
    out = BytesIO()
    doc.save(out)
    out.seek(0)
    return out.getvalue()


def _get_libreoffice_cmd() -> str:
    """Return path to LibreOffice/soffice binary (libreoffice preferred, soffice fallback)."""
    for cmd in ("libreoffice", "soffice"):
        path = shutil.which(cmd)
        if path:
            logger.info("contract_libreoffice_binary", binary=cmd, path=path)
            return path
    logger.error("libreoffice_not_found", msg="Neither libreoffice nor soffice found in PATH")
    raise RuntimeError("Конвертация DOCX в PDF недоступна: LibreOffice не найден")


def docx_to_pdf_bytes(docx_bytes: bytes) -> bytes:
    """
    Convert DOCX to PDF using headless LibreOffice (libreoffice or soffice).
    Writes docx to temp file, runs binary --headless --convert-to pdf.
    Returns PDF bytes. Logs binary used and conversion time (ms), no PII.
    """
    cmd = _get_libreoffice_cmd()
    started = time.monotonic()
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "template.docx")
        with open(docx_path, "wb") as f:
            f.write(docx_bytes)
        try:
            subprocess.run(
                [
                    cmd,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", tmpdir,
                    docx_path,
                ],
                check=True,
                capture_output=True,
                timeout=60,
                env={**os.environ, "HOME": tmpdir},
            )
        except subprocess.CalledProcessError as e:
            logger.exception(
                "contract_docx_to_pdf_failed",
                stderr=(e.stderr and e.stderr.decode(errors="replace")) or "",
                error=str(e),
            )
            raise
        except FileNotFoundError:
            logger.error("libreoffice_not_found", msg="LibreOffice not installed or not in PATH")
            raise RuntimeError("Конвертация DOCX в PDF недоступна: LibreOffice не найден") from None

        pdf_path = os.path.join(tmpdir, "template.pdf")
        if not os.path.isfile(pdf_path):
            raise RuntimeError("LibreOffice не создал PDF")

        with open(pdf_path, "rb") as f:
            result = f.read()

    elapsed_ms = int((time.monotonic() - started) * 1000)
    logger.info("contract_docx_to_pdf_done", binary=os.path.basename(cmd), elapsed_ms=elapsed_ms)
    return result


def contract_data_to_context(contract: ContractData) -> dict[str, str]:
    """Build placeholder context from ContractData (same keys as HTML template)."""
    return {
        "company_name": contract.company_name or "-",
        "inn": contract.inn or "-",
        "director": contract.director or "-",
        "bank_bik": contract.bank_bik or "-",
        "bank_account": contract.bank_account or "-",
        "contract_number": contract.contract_number or "-",
        "contract_date": contract.contract_date or "-",
        "service_description": contract.service_description or "-",
        "kpp": contract.kpp or "-",
        "ogrn": contract.ogrn or "-",
        "legal_address": contract.legal_address or "-",
        "bank_name": contract.bank_name or "-",
        "bank_corr_account": contract.bank_corr_account or "-",
    }


def render_contract_pdf_from_docx_template(
    s3: S3Service,
    file_key: str,
    file_type: str,
    docx_key: str | None,
    contract: ContractData,
) -> bytes:
    """
    Load DOCX template from S3, apply contract context, convert to PDF.
    Returns PDF bytes.
    """
    docx_bytes = get_docx_bytes_for_template(s3, file_key, file_type or "", docx_key)
    context = contract_data_to_context(contract)
    rendered_docx = render_docx_with_context(docx_bytes, context)
    return docx_to_pdf_bytes(rendered_docx)


def delete_template_files(s3: S3Service, file_key: str | None, docx_key: str | None) -> None:
    """Delete template files from S3. Ignores missing keys."""
    for key in (file_key, docx_key):
        if key:
            try:
                s3.delete_object(key)
            except Exception as e:
                logger.warning("contract_template_s3_delete_failed", key=key, error=str(e))
