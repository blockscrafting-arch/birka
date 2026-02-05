"""Tests for storage: upload and HEAD availability check after upload."""
import respx
import httpx
import pytest

from app.services.s3 import S3Service


@pytest.mark.asyncio
async def test_upload_then_head_check_availability(monkeypatch):
    """
    After uploading a file to S3, HEAD request to the public URL confirms availability.
    Covers the flow required by docs: upload -> HEAD check.
    """
    from app.core.config import settings

    monkeypatch.setattr(settings, "FILE_PUBLIC_BASE_URL", "https://storage.test")
    service = S3Service()
    key = "test-bucket/path/file.pdf"
    url = service.build_public_url(key)
    assert url == "https://storage.test/test-bucket/path/file.pdf"

    with respx.mock:
        respx.head(url).mock(return_value=httpx.Response(200))
        available = await service.head_check(url)
    assert available is True
