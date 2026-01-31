"""S3 storage service."""
from io import BytesIO
from typing import BinaryIO

import boto3
import httpx

from app.core.config import settings


class S3Service:
    """S3 helper for uploads and URL building."""

    def __init__(self) -> None:
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
        )

    def upload_bytes(self, key: str, data: bytes, content_type: str) -> str:
        """Upload bytes without multipart (non-chunked)."""
        stream: BinaryIO = BytesIO(data)
        self.client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=stream,
            ContentType=content_type,
        )
        return key

    def build_public_url(self, key: str) -> str:
        """Build public URL from key."""
        base = settings.FILE_PUBLIC_BASE_URL.rstrip("/")
        return f"{base}/{key}"

    async def head_check(self, url: str) -> bool:
        """Check URL availability with HEAD request."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.head(url)
            return response.status_code < 400
        except httpx.HTTPError:
            return False
