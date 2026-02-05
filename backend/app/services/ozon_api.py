"""Ozon Seller API client for FBO supplies.
Docs: https://docs.ozon.ru/api/seller/
Authorization: Headers Client-Id, Api-Key
"""

import httpx

from app.core.logging import logger

SELLER_BASE_URL = "https://api-seller.ozon.ru"


class OzonAPI:
    """Client for Ozon Seller API (FBO supplies, labels)."""

    def __init__(self, client_id: str, api_key: str) -> None:
        self.client_id = client_id
        self.api_key = api_key
        self._headers = {"Client-Id": client_id, "Api-Key": api_key, "Content-Type": "application/json"}

    async def list_supply_orders(self) -> list[dict]:
        """List FBO supply orders. POST /v2/supply-order/list."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{SELLER_BASE_URL}/v2/supply-order/list",
                    headers=self._headers,
                    json={},
                )
                r.raise_for_status()
                data = r.json()
                return data.get("result", {}).get("items", []) or []
        except Exception as e:
            logger.warning("ozon_api_supply_list_failed", error=str(e))
            return []

    async def get_supply_order(self, supply_id: int) -> dict | None:
        """Get FBO supply order details. POST /v2/supply-order/get."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{SELLER_BASE_URL}/v2/supply-order/get",
                    headers=self._headers,
                    json={"id": supply_id},
                )
                r.raise_for_status()
                return r.json().get("result")
        except Exception as e:
            logger.warning("ozon_api_supply_get_failed", supply_id=supply_id, error=str(e))
            return None
