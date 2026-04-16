"""Periodic cleanup of orphaned S3 objects not referenced in DB."""
from celery import shared_task
from sqlalchemy import select

from app.db.session import SyncSessionLocal
from app.db.models.order_photo import OrderPhoto
from app.db.models.product import ProductPhoto
from app.db.models.contract_template import ContractTemplate
from app.core.logging import logger
from app.services.s3 import S3Service
from app.core.config import settings


@shared_task(
    name="app.tasks.s3_cleanup.cleanup_orphaned_s3_objects",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=1,
)
def cleanup_orphaned_s3_objects() -> int:
    """List S3 objects and delete those not referenced in DB.

    Runs weekly via Celery Beat. Only cleans known prefixes (photos/, templates/).
    """
    if not settings.S3_BUCKET_NAME or not settings.S3_ENDPOINT_URL:
        return 0

    s3 = S3Service()
    client = s3._get_client()
    deleted = 0

    with SyncSessionLocal() as db:
        # Collect all known S3 keys from DB
        order_photo_keys = set(
            row[0] for row in db.execute(select(OrderPhoto.s3_key)).all()
        )
        product_photo_keys = set(
            row[0] for row in db.execute(select(ProductPhoto.s3_key)).all()
        )
        template_keys = set()
        for row in db.execute(select(ContractTemplate.file_key, ContractTemplate.docx_key)).all():
            if row[0]:
                template_keys.add(row[0])
            if row[1]:
                template_keys.add(row[1])

        known_keys = order_photo_keys | product_photo_keys | template_keys

    # List S3 objects in known prefixes (orders/, products/, contract-templates/)
    for prefix in ("orders/", "products/", "contract-templates/"):
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=settings.S3_BUCKET_NAME, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key not in known_keys:
                    try:
                        s3.delete_object(key)
                        deleted += 1
                    except Exception as exc:
                        logger.warning("s3_cleanup_delete_failed", key=key, error=str(exc))

    if deleted:
        logger.info("s3_cleanup_done", deleted=deleted)
    return deleted
