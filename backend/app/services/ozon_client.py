"""Ozon Seller API client for FBO and warehouses."""

import asyncio
from typing import Any

import httpx

from app.core.logging import logger

OZON_BASE = "https://api-seller.ozon.ru"


class OzonClient:
    """Client for Ozon Seller API (FBO postings, warehouses, supply drafts, labels)."""

    def __init__(self, client_id: str, api_key: str) -> None:
        self.client_id = client_id
        self.api_key = api_key
        self._headers = {
            "Client-Id": client_id,
            "Api-Key": api_key,
            "Content-Type": "application/json",
        }

    async def get_products_by_offer_id(self, offer_ids: list[str]) -> dict[str, int]:
        """Resolve offer_id -> sku via POST /v3/product/info/list. Returns mapping offer_id -> sku."""
        if not offer_ids:
            return {}
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                r = await client.post(
                    f"{OZON_BASE}/v3/product/info/list",
                    headers=self._headers,
                    json={"offer_id": list(offer_ids)},
                )
                r.raise_for_status()
                data = r.json()
                items = data.get("result", {}).get("items", []) if isinstance(data, dict) else []
                result: dict[str, int] = {}
                for it in items if isinstance(items, list) else []:
                    if isinstance(it, dict):
                        oid = it.get("offer_id")
                        sku = it.get("sku")
                        if oid is not None and sku is not None:
                            result[str(oid)] = int(sku)
                return result
            except httpx.HTTPError as exc:
                logger.warning("ozon_product_info_failed", error=str(exc))
                return {}

    async def get_warehouses(self) -> list[dict[str, Any]]:
        """Return list of warehouses (POST /v1/warehouse/list)."""
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                r = await client.post(
                    f"{OZON_BASE}/v1/warehouse/list",
                    headers=self._headers,
                    json={},
                )
                r.raise_for_status()
                data = r.json()
                result = data.get("result", []) if isinstance(data, dict) else []
                return result if isinstance(result, list) else []
            except httpx.HTTPError as exc:
                logger.warning("ozon_warehouses_failed", error=str(exc))
                return []

    async def get_fbo_postings(self, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        """Return FBO postings list (GET /v2/posting/fbo/list)."""
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                r = await client.get(
                    f"{OZON_BASE}/v2/posting/fbo/list",
                    headers=self._headers,
                    params={"limit": limit, "offset": offset},
                )
                r.raise_for_status()
                return r.json()
            except httpx.HTTPError as exc:
                logger.warning("ozon_fbo_list_failed", error=str(exc))
                return {"result": {"postings": [], "total": 0}}

    async def create_supply_draft(
        self, items: list[dict[str, Any]], supply_type: str = "CREATE_TYPE_DIRECT"
    ) -> str | None:
        """Create draft supply (POST /v1/draft/create). items: [{"sku": int, "quantity": int}, ...]. Returns operation_id."""
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                r = await client.post(
                    f"{OZON_BASE}/v1/draft/create",
                    headers=self._headers,
                    json={"items": items, "type": supply_type},
                )
                r.raise_for_status()
                body = r.json()
                return body.get("operation_id") if isinstance(body, dict) else None
            except httpx.HTTPError as exc:
                logger.warning("ozon_draft_create_failed", error=str(exc))
                return None

    async def get_draft_create_info(self, operation_id: str) -> dict[str, Any] | None:
        """Poll draft creation status (POST /v1/draft/create/info). Returns result with draft_id, warehouse_id, timeslots when ready."""
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                for _ in range(60):
                    r = await client.post(
                        f"{OZON_BASE}/v1/draft/create/info",
                        headers=self._headers,
                        json={"operation_id": operation_id},
                    )
                    r.raise_for_status()
                    data = r.json()
                    status = (data.get("result") or data or {}).get("status") if isinstance(data, dict) else None
                    if status == "SUCCESS" or status == "DraftCreateStatusSuccess":
                        return data.get("result") if isinstance(data, dict) else data
                    if status and "FAIL" in str(status).upper():
                        return None
                    await asyncio.sleep(1)
                return None
            except httpx.HTTPError as exc:
                logger.warning("ozon_draft_create_info_failed", error=str(exc))
                return None

    async def create_supply_from_draft(self, draft_id: int, warehouse_id: int, timeslot: dict[str, str]) -> str | None:
        """Create supply from draft (POST /v1/draft/supply/create). Returns operation_id."""
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                r = await client.post(
                    f"{OZON_BASE}/v1/draft/supply/create",
                    headers=self._headers,
                    json={
                        "draft_id": draft_id,
                        "warehouse_id": warehouse_id,
                        "timeslot": timeslot,
                    },
                )
                r.raise_for_status()
                body = r.json()
                return body.get("operation_id") if isinstance(body, dict) else None
            except httpx.HTTPError as exc:
                logger.warning("ozon_draft_supply_create_failed", error=str(exc))
                return None

    async def get_supply_create_status(self, operation_id: str) -> list[int] | None:
        """Poll supply creation status. Returns list of supply_id when success."""
        async with httpx.AsyncClient(timeout=120) as client:
            try:
                for _ in range(90):
                    r = await client.post(
                        f"{OZON_BASE}/v1/supply/create/status",
                        headers=self._headers,
                        json={"operation_id": operation_id},
                    )
                    r.raise_for_status()
                    data = r.json()
                    result = data.get("result") if isinstance(data, dict) else None
                    status = (data.get("status") or (result or {}).get("status")) if isinstance(data, dict) else None
                    if status in ("DraftSupplyCreateStatusSuccess", "SUCCESS"):
                        order_ids = (result or data or {}).get("order_ids") or (result or data or {}).get("supply_ids")
                        if order_ids and isinstance(order_ids, list):
                            out = []
                            for oid in order_ids:
                                try:
                                    out.append(int(oid))
                                except (TypeError, ValueError):
                                    pass
                            return out if out else None
                        return None
                    if status and "FAIL" in str(status).upper():
                        return None
                    await asyncio.sleep(2)
                return None
            except httpx.HTTPError as exc:
                logger.warning("ozon_supply_create_status_failed", error=str(exc))
                return None

    async def create_cargoes(self, supply_id: int, cargoes: list[list[dict[str, Any]]]) -> str | None:
        """Set cargo composition (POST /v1/cargoes/create). cargoes: list of boxes, each box = list of {offer_id, quantity}. Returns operation_id."""
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                payload = {
                    "supply_id": supply_id,
                    "cargoes": [
                        {
                            "key": str(i),
                            "value": {
                                "items": [
                                    {
                                        "offer_id": str(it.get("offer_id", "")),
                                        "quantity": int(it.get("quantity", it.get("quant", 0))),
                                    }
                                    for it in box
                                ],
                                "type": "BOX",
                            },
                        }
                        for i, box in enumerate(cargoes)
                    ],
                }
                r = await client.post(
                    f"{OZON_BASE}/v1/cargoes/create",
                    headers=self._headers,
                    json=payload,
                )
                r.raise_for_status()
                body = r.json()
                return body.get("operation_id") if isinstance(body, dict) else None
            except httpx.HTTPError as exc:
                logger.warning("ozon_cargoes_create_failed", error=str(exc))
                return None

    async def get_cargoes_create_info(self, operation_id: str) -> list[str] | None:
        """Poll cargoes create status (POST /v2/cargoes/create/info). Returns list of cargo_id (or keys) per box."""
        async with httpx.AsyncClient(timeout=120) as client:
            try:
                for _ in range(60):
                    r = await client.post(
                        f"{OZON_BASE}/v2/cargoes/create/info",
                        headers=self._headers,
                        json={"operation_id": operation_id},
                    )
                    r.raise_for_status()
                    data = r.json()
                    result = data.get("result") if isinstance(data, dict) else None
                    status = (result or data or {}).get("status") if isinstance(data, dict) else None
                    if status in ("SUCCESS", "CargoesCreateStatusSuccess"):
                        cargoes = (result or {}).get("cargoes") or (result or {}).get("cargo_ids")
                        if cargoes is not None and isinstance(cargoes, list):
                            out = []
                            for c in cargoes:
                                if isinstance(c, dict):
                                    cid = c.get("cargo_id") or c.get("id") or c.get("key")
                                    if cid is not None:
                                        out.append(str(cid))
                                else:
                                    out.append(str(c))
                            return out if out else None
                        return None
                    if status and "FAIL" in str(status).upper():
                        return None
                    await asyncio.sleep(2)
                return None
            except httpx.HTTPError as exc:
                logger.warning("ozon_cargoes_create_info_failed", error=str(exc))
                return None

    async def get_supply_labels(self, supply_id: int, cargo_ids: list[int] | list[str]) -> bytes | None:
        """Create label task, poll status, then download PDF. cargo_ids are external cargo_id from Ozon. Returns PDF bytes or None."""
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                payload = {
                    "supply_id": supply_id,
                    "cargoes": [
                        {"cargo_id": int(cid) if isinstance(cid, str) and cid.isdigit() else cid} for cid in cargo_ids
                    ],
                }
                r = await client.post(
                    f"{OZON_BASE}/v1/cargoes-label/create",
                    headers=self._headers,
                    json=payload,
                )
                r.raise_for_status()
                body = r.json()
                operation_id = (body.get("result") or body).get("operation_id") if isinstance(body, dict) else None
                if not operation_id:
                    return None
                for _ in range(30):
                    await asyncio.sleep(1)
                    r2 = await client.post(
                        f"{OZON_BASE}/v1/cargoes-label/get",
                        headers=self._headers,
                        json={"operation_id": operation_id},
                    )
                    r2.raise_for_status()
                    info = r2.json()
                    status = info.get("status", "")
                    if status == "SUCCESS":
                        file_guid = (info.get("result") or {}).get("file_guid")
                        if file_guid:
                            r3 = await client.get(
                                f"{OZON_BASE}/v1/cargoes-label/file/{file_guid}",
                                headers={"Client-Id": self.client_id, "Api-Key": self.api_key},
                            )
                            r3.raise_for_status()
                            return r3.content
                        break
                    if status == "FAILED":
                        break
                return None
            except httpx.HTTPError as exc:
                logger.warning("ozon_labels_failed", error=str(exc))
                return None
