"""Document conversion tasks (run in Celery worker with LibreOffice)."""
import base64

from app.celery_app import celery_app
from app.services.contract_template_service import docx_to_pdf_bytes, rtf_to_docx_bytes


@celery_app.task(
    bind=True,
    name="app.tasks.document_tasks.convert_rtf_to_docx",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=2,
)
def convert_rtf_to_docx_task(self, rtf_base64: str) -> str:
    """Convert RTF to DOCX in worker. Returns base64-encoded DOCX bytes."""
    rtf_bytes = base64.b64decode(rtf_base64)
    docx_bytes = rtf_to_docx_bytes(rtf_bytes)
    return base64.b64encode(docx_bytes).decode("ascii")


@celery_app.task(
    bind=True,
    name="app.tasks.document_tasks.convert_docx_to_pdf",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=2,
)
def convert_docx_to_pdf_task(self, docx_base64: str) -> str:
    """Convert DOCX to PDF in worker. Returns base64-encoded PDF bytes."""
    docx_bytes = base64.b64decode(docx_base64)
    pdf_bytes = docx_to_pdf_bytes(docx_bytes)
    return base64.b64encode(pdf_bytes).decode("ascii")
