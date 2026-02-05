"""Tests for Ozon API barcode parsing."""
import pytest

from app.services.ozon_api import OzonAPI


@pytest.mark.asyncio
async def test_get_supply_barcodes_from_barcodes():
    """Barcodes in order.barcodes."""
    api = OzonAPI(client_id="c", api_key="k")

    async def mock_get(_):
        return {"barcodes": ["BC1", "BC2"]}

    api.get_supply_order = mock_get
    out = await api.get_supply_barcodes(1)
    assert out == ["BC1", "BC2"]


@pytest.mark.asyncio
async def test_get_supply_barcodes_from_package():
    """Barcodes in order.package.barcodes."""
    api = OzonAPI(client_id="c", api_key="k")

    async def mock_get(_):
        return {"package": {"barcodes": ["P1", "P2"]}}

    api.get_supply_order = mock_get
    out = await api.get_supply_barcodes(1)
    assert out == ["P1", "P2"]


@pytest.mark.asyncio
async def test_get_supply_barcodes_from_packages():
    """Barcodes in order.packages[0].barcodes."""
    api = OzonAPI(client_id="c", api_key="k")

    async def mock_get(_):
        return {"packages": [{"barcodes": ["PK1", "PK2"]}]}

    api.get_supply_order = mock_get
    out = await api.get_supply_barcodes(1)
    assert out == ["PK1", "PK2"]


@pytest.mark.asyncio
async def test_get_supply_barcodes_empty_barcodes_tries_packages():
    """When barcodes is [], fallback to packages."""
    api = OzonAPI(client_id="c", api_key="k")

    async def mock_get(_):
        return {"barcodes": [], "packages": [{"barcodes": ["F1"]}]}

    api.get_supply_order = mock_get
    out = await api.get_supply_barcodes(1)
    assert out == ["F1"]


@pytest.mark.asyncio
async def test_get_supply_barcodes_none_order():
    """None order returns []."""
    api = OzonAPI(client_id="c", api_key="k")

    async def mock_get(_):
        return None

    api.get_supply_order = mock_get
    out = await api.get_supply_barcodes(1)
    assert out == []
