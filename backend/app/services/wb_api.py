"""Wildberries API client for FBW supplies.

Docs: https://openapi.wildberries.ru/marketplace/swagger/api/en/ (Supplies, v3)
Authorization: Header Authorization: {API_KEY}
"""

import httpx

from app.core.logging import logger

SUPPLIES_BASE_URL = "https://marketplace-api.wildberries.ru"


class WildberriesAPI:
    """Client for Wildberries supplies API (FBW, v3)."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._headers = {"Authorization": api_key}

    async def create_supply(self, name: str = "Поставка") -> str | None:
        """Create a new supply. POST /api/v3/supplies. Returns supply ID (WB-GI-xxx) or None."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{SUPPLIES_BASE_URL}/api/v3/supplies",
                    headers=self._headers,
                    json={"name": name},
                )
                if r.status_code in (401, 403):
                    logger.warning("wb_api_create_supply_unauthorized", status=r.status_code)
                    return None
                r.raise_for_status()
                data = r.json()
                return data.get("id")
        except Exception as e:
            logger.warning("wb_api_create_supply_failed", error=str(e))
            return None

    async def get_supplies(self, limit: int = 1000, next_: int = 0) -> list | None:
        """List supplies. GET /api/v3/supplies. Returns None on auth/connection error."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"{SUPPLIES_BASE_URL}/api/v3/supplies",
                    headers=self._headers,
                    params={"limit": limit, "next": next_},
                )
                if r.status_code in (401, 403):
                    logger.warning("wb_api_supplies_unauthorized", status=r.status_code)
                    return None
                r.raise_for_status()
                data = r.json() or {}
                return data.get("supplies") or []
        except Exception as e:
            logger.warning("wb_api_supplies_failed", error=str(e))
            return None

    async def create_supply_boxes(self, supply_id: str, amount: int) -> list[str]:
        """Create boxes in a supply. POST /api/v3/supplies/{supplyId}/trbx. Returns list of trbx IDs."""
        if amount < 1 or amount > 1000:
            return []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{SUPPLIES_BASE_URL}/api/v3/supplies/{supply_id}/trbx",
                    headers=self._headers,
                    json={"amount": amount},
                )
                if r.status_code in (401, 403):
                    logger.warning("wb_api_create_boxes_unauthorized", status=r.status_code)
                    return []
                r.raise_for_status()
                data = r.json() or {}
                ids = data.get("trbxIds") or []
                return [str(i) for i in ids]
        except Exception as e:
            logger.warning(
                "wb_api_create_boxes_failed", supply_id=supply_id, amount=amount, error=str(e)
            )
            return []

    async def add_order_to_supply(self, supply_id: str, order_id: int) -> bool:
        """Add order to supply (moves to confirm). PATCH /api/v3/supplies/{supplyId}/orders/{orderId}."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.patch(
                    f"{SUPPLIES_BASE_URL}/api/v3/supplies/{supply_id}/orders/{order_id}",
                    headers=self._headers,
                )
                if r.status_code in (401, 403):
                    logger.warning("wb_api_add_order_unauthorized", status=r.status_code)
                    return False
                r.raise_for_status()
                return True
        except Exception as e:
            logger.warning(
                "wb_api_add_order_failed",
                supply_id=supply_id,
                order_id=order_id,
                error=str(e),
            )
            return False

    async def get_supply_boxes(self, supply_id: str) -> list[dict]:
        """Get boxes (trbx) for a supply. GET /api/v3/supplies/{supplyId}/trbx."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"{SUPPLIES_BASE_URL}/api/v3/supplies/{supply_id}/trbx",
                    headers=self._headers,
                )
                r.raise_for_status()
                data = r.json() or {}
                return data.get("trbxes") or []
        except Exception as e:
            logger.warning("wb_api_supply_boxes_failed", supply_id=supply_id, error=str(e))
            return []

    async def get_supply_package(self, supply_id: str) -> list:
        """Get package (box) barcodes for a supply. Uses v3 trbx, returns list of box IDs."""
        boxes = await self.get_supply_boxes(supply_id)
        return [b.get("id") for b in boxes if b.get("id")]

    async def get_barcodes(self, supply_id: str) -> list[str]:
        """Get package (box) barcodes for a supply. Returns list of barcode/box ID strings."""
        raw = await self.get_supply_package(supply_id)
        if isinstance(raw, list):
            return [str(x) for x in raw if x]
        return []

    async def get_box_stickers(
        self, supply_id: str, trbx_ids: list[str], fmt: str = "png"
    ) -> list[dict]:
        """Get box stickers. POST /api/v3/supplies/{supplyId}/trbx/stickers."""
        if not trbx_ids:
            return []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{SUPPLIES_BASE_URL}/api/v3/supplies/{supply_id}/trbx/stickers",
                    headers=self._headers,
                    params={"type": fmt},
                    json={"trbxIds": trbx_ids},
                )
                r.raise_for_status()
                data = r.json() or {}
                return data.get("stickers") or []
        except Exception as e:
            logger.warning(
                "wb_api_box_stickers_failed",
                supply_id=supply_id,
                error=str(e),
            )
            return []
