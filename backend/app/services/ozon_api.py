"""Ozon Seller API client for FBO supplies.
Docs: https://docs.ozon.ru/api/seller/
Authorization: Headers Client-Id, Api-Key
"""

from contextlib import asynccontextmanager

import httpx

from app.core.logging import logger

SELLER_BASE_URL = "https://api-seller.ozon.ru"


@asynccontextmanager
async def _client_or_new(client: httpx.AsyncClient | None):
    """Yield shared client or a new one (closed on exit)."""
    if client is not None:
        yield client
    else:
        async with httpx.AsyncClient(timeout=30) as new_client:
            yield new_client


class OzonAPI:
    """Client for Ozon Seller API (FBO supplies, labels)."""

    def __init__(self, client_id: str, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        self.client_id = client_id
        self.api_key = api_key
        self._headers = {"Client-Id": client_id, "Api-Key": api_key, "Content-Type": "application/json"}
        self._client = client

    def _client_ctx(self):
        """Context manager: shared client or new AsyncClient."""
        return _client_or_new(self._client)

    async def list_supply_orders(self) -> list[dict] | None:
        """List FBO supply orders. POST /v2/supply-order/list. Returns None on auth/connection error."""
        try:
            async with self._client_ctx() as client:
                r = await client.post(
                    f"{SELLER_BASE_URL}/v2/supply-order/list",
                    headers=self._headers,
                    json={},
                )
                if r.status_code in (401, 403):
                    logger.warning("ozon_api_supply_list_unauthorized", status=r.status_code)
                    return None
                r.raise_for_status()
                data = r.json()
                return data.get("result", {}).get("items", []) or []
        except httpx.HTTPStatusError as e:
            logger.warning("ozon_api_supply_list_failed", status=e.response.status_code, error=str(e))
            return None
        except (httpx.RequestError, httpx.TimeoutException) as e:
            logger.warning("ozon_api_supply_list_failed", error=str(e))
            return None

    async def get_supply_order(self, supply_id: int) -> dict | None:
        """Get FBO supply order details. POST /v2/supply-order/get."""
        try:
            async with self._client_ctx() as client:
                r = await client.post(
                    f"{SELLER_BASE_URL}/v2/supply-order/get",
                    headers=self._headers,
                    json={"id": supply_id},
                )
                if r.status_code in (401, 403):
                    logger.warning("ozon_api_supply_get_unauthorized", status=r.status_code)
                    return None
                r.raise_for_status()
                return r.json().get("result")
        except httpx.HTTPStatusError as e:
            logger.warning("ozon_api_supply_get_failed", supply_id=supply_id, status=e.response.status_code, error=str(e))
            return None
        except (httpx.RequestError, httpx.TimeoutException) as e:
            logger.warning("ozon_api_supply_get_failed", supply_id=supply_id, error=str(e))
            return None

    async def create_supply_draft(
        self,
        items: dict[str, int] | None = None,
        cluster_id: str | None = None,
    ) -> int | str | None:
        """
        Create FBO supply order draft. POST /v2/supply-order/create or similar.
        items: sku -> quantity. Returns supply order id or None on error.
        """
        try:
            async with self._client_ctx() as client:
                body: dict = {}
                if items:
                    body["items"] = [{"sku": sku, "quantity": qty} for sku, qty in items.items()]
                if cluster_id:
                    body["cluster_id"] = cluster_id
                r = await client.post(
                    f"{SELLER_BASE_URL}/v2/supply-order/create",
                    headers=self._headers,
                    json=body,
                )
                if r.status_code in (401, 403):
                    logger.warning("ozon_api_create_supply_unauthorized", status=r.status_code)
                    return None
                r.raise_for_status()
                data = r.json()
                result = data.get("result") if isinstance(data, dict) else None
                if result is not None and "id" in result:
                    return result["id"]
                if isinstance(data, dict) and "operation_id" in data:
                    return data["operation_id"]
                logger.warning("ozon_api_create_supply_unexpected_response", data=data)
                return None
        except httpx.HTTPStatusError as e:
            logger.warning("ozon_api_create_supply_failed", status=e.response.status_code, error=str(e))
            return None
        except (httpx.RequestError, httpx.TimeoutException) as e:
            logger.warning("ozon_api_create_supply_failed", error=str(e))
            return None

    async def get_supply_barcodes(self, supply_id: int) -> list[str]:
        """Get barcodes for FBO supply order (from package/boxes if available)."""
        order = await self.get_supply_order(supply_id)
        if not order or not isinstance(order, dict):
            return []
        barcodes = order.get("barcodes") or order.get("package", {}).get("barcodes")
        if barcodes is None:
            packages = order.get("packages") or []
            barcodes = packages[0].get("barcodes") if packages else []
        if not barcodes or not isinstance(barcodes, list):
            barcodes = []
        return [str(b) for b in barcodes]
