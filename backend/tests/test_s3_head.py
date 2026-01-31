"""Tests for S3 head checks."""
import respx
import httpx

import pytest

from app.services.s3 import S3Service


@pytest.mark.asyncio
async def test_head_check_success():
    """HEAD check returns true on 200."""
    service = S3Service()
    with respx.mock:
        respx.head("https://example.com/file.jpg").mock(return_value=httpx.Response(200))
        assert await service.head_check("https://example.com/file.jpg") is True


@pytest.mark.asyncio
async def test_head_check_failure():
    """HEAD check returns false on 404."""
    service = S3Service()
    with respx.mock:
        respx.head("https://example.com/missing.jpg").mock(return_value=httpx.Response(404))
        assert await service.head_check("https://example.com/missing.jpg") is False
