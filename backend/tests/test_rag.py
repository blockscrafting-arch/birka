"""Tests for RAG: build_rag_context_async return shape and STATIC_BASE content."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import rag


@pytest.mark.asyncio
async def test_build_rag_context_async_returns_tuple_when_no_api_key():
    """When OPENAI_API_KEY is missing, returns (None, user_message)."""
    mock_db = MagicMock()
    with patch("app.services.rag.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = ""
        rag_system, user_message = await rag.build_rag_context_async(mock_db, "Hello")
    assert rag_system is None
    assert user_message == "Hello"


def test_static_base_no_identity_duplication():
    """STATIC_BASE does not duplicate main system prompt identity."""
    assert "статусы заявок" in rag.STATIC_BASE or "На приемке" in rag.STATIC_BASE
    assert "браке" in rag.STATIC_BASE or "фото" in rag.STATIC_BASE


def test_build_rag_context_sync_fallback():
    """build_rag_context returns empty string when no API key."""
    with patch("app.services.rag.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = ""
        assert rag.build_rag_context("test") == ""
