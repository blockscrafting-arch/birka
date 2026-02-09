"""Wildberries API client for supplies and warehouses."""
from typing import Any

import httpx

from app.core.logging import logger

WB_SUPPLIES_BASE = "https://supplies-api.wildberries.ru"
WB_CONTENT_BASE = "https://content-api.wildberries.ru"


class WBClient:
    """Client for Wildberries seller API (supplies, warehouses)."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._headers = {"Authorization": api_key}

    async def get_warehouses(self) -> list[dict[str, Any]]:
        """Return list of seller warehouses (GET /api/v3/warehouses)."""
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                r = await client.get(
                    f"{WB_SUPPLIES_BASE}/api/v3/warehouses",
                    headers=self._headers,
                )
                r.raise_for_status()
                data = r.json()
                return data.get("warehouses", []) if isinstance(data, dict) else []
            except httpx.HTTPError as exc:
                logger.warning("wb_warehouses_failed", error=str(exc))
                return []

    async def get_supplies(self, next_cursor: str | None = None) -> dict[str, Any]:
        """Return list of supplies. Optional cursor for pagination."""
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                params = {}
                if next_cursor:
                    params["next"] = next_cursor
                r = await client.get(
                    f"{WB_SUPPLIES_BASE}/api/v3/supplies",
                    headers=self._headers,
                    params=params or None,
                )
                r.raise_for_status()
                return r.json()
            except httpx.HTTPError as exc:
                logger.warning("wb_supplies_failed", error=str(exc))
                return {"supplies": [], "nextCursor": None}

    async def create_supply(self, name: str) -> dict[str, Any] | None:
        """Create a supply; returns {'id': 'WB-GI-...'} or None."""
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                r = await client.post(
                    f"{WB_SUPPLIES_BASE}/api/v3/supplies",
                    headers={**self._headers, "Content-Type": "application/json"},
                    json={"name": name[:128]},
                )
                r.raise_for_status()
                return r.json()
            except httpx.HTTPError as exc:
                logger.warning("wb_create_supply_failed", error=str(exc))
                return None

    async def get_supply_barcode(
        self, supply_id: str, fmt: str = "png"
    ) -> tuple[bytes | None, str]:
        """Get supply QR/barcode (GET /api/v3/supplies/{supplyId}/barcode). Returns (bytes, media_type) or (None, ''). Available after supply is transferred for delivery."""
        if not supply_id or not supply_id.strip():
            return None, ""
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                r = await client.get(
                    f"{WB_SUPPLIES_BASE}/api/v3/supplies/{supply_id.strip()}/barcode",
                    headers=self._headers,
                    params={"type": fmt},
                )
                r.raise_for_status()
                content = r.content
                media = "image/png" if fmt == "png" else "image/svg+xml" if fmt == "svg" else "application/x-zpl"
                return content, media
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    logger.info("wb_supply_barcode_not_ready", supply_id=supply_id)
                else:
                    logger.warning("wb_supply_barcode_failed", supply_id=supply_id, error=str(exc))
                return None, ""
            except httpx.HTTPError as exc:
                logger.warning("wb_supply_barcode_failed", supply_id=supply_id, error=str(exc))
                return None, ""

    async def get_supply_box_stickers(
        self, supply_id: str, sticker_type: str = "png", width: int = 58, height: int = 40
    ) -> list[dict[str, Any]]:
        """Get box stickers for supply (POST /api/v3/supplies/{supplyId}/trbx/stickers). Returns list of {barcode, file (base64)}."""
        if not supply_id or not supply_id.strip():
            return []
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                r = await client.post(
                    f"{WB_SUPPLIES_BASE}/api/v3/supplies/{supply_id.strip()}/trbx/stickers",
                    headers={**self._headers, "Content-Type": "application/json"},
                    params={"type": sticker_type, "width": width, "height": height},
                    json={},
                )
                r.raise_for_status()
                data = r.json()
                return data.get("stickers", []) if isinstance(data, dict) else []
            except httpx.HTTPError as exc:
                logger.warning("wb_supply_trbx_stickers_failed", supply_id=supply_id, error=str(exc))
                return []

    async def get_supply_stickers(
        self, order_ids: list[int], sticker_type: str = "png", width: int = 58, height: int = 40
    ) -> list[dict[str, Any]]:
        """Get stickers for FBS orders (POST /api/v3/orders/stickers). Returns list of {orderId, barcode, file (base64)}. For FBO supply labels use get_supply_barcode or get_supply_box_stickers."""
        if not order_ids or len(order_ids) > 100:
            return []
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                r = await client.post(
                    f"{WB_SUPPLIES_BASE}/api/v3/orders/stickers",
                    headers={**self._headers, "Content-Type": "application/json"},
                    params={"type": sticker_type, "width": width, "height": height},
                    json={"orders": order_ids[:100]},
                )
                r.raise_for_status()
                data = r.json()
                return data.get("stickers", []) if isinstance(data, dict) else []
            except httpx.HTTPError as exc:
                logger.warning("wb_stickers_failed", error=str(exc))
                return []
