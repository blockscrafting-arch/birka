"""Wildberries API client for FBW supplies.

Docs: https://openapi.wb.ru/supplies/api/ru/
Authorization: Header Authorization: {API_KEY}
"""

import httpx

from app.core.logging import logger

SUPPLIES_BASE_URL = "https://supplies-api.wildberries.ru"


class WildberriesAPI:
    """Client for Wildberries supplies API (FBW)."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._headers = {"Authorization": api_key}

    async def get_supplies(self, limit: int = 1000) -> list | None:
        """List supplies. POST /api/v1/supplies. Returns None on auth/connection error."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{SUPPLIES_BASE_URL}/api/v1/supplies",
                    headers=self._headers,
                    json={},
                )
                if r.status_code in (401, 403):
                    logger.warning("wb_api_supplies_unauthorized", status=r.status_code)
                    return None
                r.raise_for_status()
                return r.json() or []
        except Exception as e:
            logger.warning("wb_api_supplies_failed", error=str(e))
            return None

    async def get_supply_package(self, supply_id: str) -> list:
        """Get package (box) barcodes for a supply. GET /api/v1/supplies/{id}/package."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"{SUPPLIES_BASE_URL}/api/v1/supplies/{supply_id}/package",
                    headers=self._headers,
                )
                r.raise_for_status()
                return r.json() or []
        except Exception as e:
            logger.warning("wb_api_supply_package_failed", supply_id=supply_id, error=str(e))
            return []

    async def get_barcodes(self, supply_id: str) -> list[str]:
        """Get package (box) barcodes for a supply. Alias for get_supply_package, returns list of barcode strings."""
        raw = await self.get_supply_package(supply_id)
        if isinstance(raw, list):
            return [str(x) for x in raw if x]
        return []
