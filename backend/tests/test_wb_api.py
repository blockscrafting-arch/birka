"""Tests for WB API (with mocked httpx)."""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.wb_api import WildberriesAPI


@pytest.mark.asyncio
async def test_create_supply_returns_id():
    """create_supply returns supply id from response."""
    api = WildberriesAPI(api_key="test-key")
    with patch("httpx.AsyncClient") as mock_client:
        mock_post = AsyncMock()
        mock_post.status_code = 201
        mock_post.json.return_value = {"id": "WB-GI-1234567"}
        mock_post.raise_for_status = AsyncMock()
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_post)
        out = await api.create_supply(name="Test")
    assert out == "WB-GI-1234567"


@pytest.mark.asyncio
async def test_get_supply_boxes_returns_trbxes():
    """get_supply_boxes returns list of box dicts."""
    api = WildberriesAPI(api_key="test-key")
    with patch("httpx.AsyncClient") as mock_client:
        mock_get = AsyncMock()
        mock_get.status_code = 200
        mock_get.json.return_value = {"trbxes": [{"id": "WB-TRBX-1"}, {"id": "WB-TRBX-2"}]}
        mock_get.raise_for_status = AsyncMock()
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_get)
        out = await api.get_supply_boxes("WB-GI-123")
    assert len(out) == 2
    assert out[0]["id"] == "WB-TRBX-1"
    assert out[1]["id"] == "WB-TRBX-2"


@pytest.mark.asyncio
async def test_get_barcodes_from_boxes():
    """get_barcodes returns list of box id strings."""
    api = WildberriesAPI(api_key="test-key")
    with patch.object(api, "get_supply_boxes", new_callable=AsyncMock) as mock_boxes:
        mock_boxes.return_value = [{"id": "WB-TRBX-A"}, {"id": "WB-TRBX-B"}]
        out = await api.get_barcodes("WB-GI-123")
    assert out == ["WB-TRBX-A", "WB-TRBX-B"]
