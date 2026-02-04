"""S3 storage service."""
from io import BytesIO
from typing import BinaryIO

import boto3
import httpx

from app.core.config import settings


class S3Service:
    """S3 helper for uploads and URL building."""

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        """Create and cache an S3 client instance."""
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                region_name=settings.S3_REGION,
            )
        return self._client

    def upload_bytes(self, key: str, data: bytes, content_type: str) -> str:
        """Upload bytes without multipart (non-chunked)."""
        stream: BinaryIO = BytesIO(data)
        self._get_client().put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=stream,
            ContentType=content_type,
        )
        return key

    def get_bytes(self, key: str) -> bytes:
        """Download object from S3 and return bytes."""
        response = self._get_client().get_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
        return response["Body"].read()

    def stream_chunks(self, key: str, chunk_size: int = 65536):
        """
        Download object from S3 as a generator of chunks (for streaming response).
        Yields bytes chunks; the S3 response body is read in the same thread that calls next().
        """
        response = self._get_client().get_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
        body = response["Body"]
        for chunk in iter(lambda: body.read(chunk_size), b""):
            yield chunk

    def delete_object(self, key: str) -> None:
        """Delete object from S3 by key."""
        self._get_client().delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)

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
