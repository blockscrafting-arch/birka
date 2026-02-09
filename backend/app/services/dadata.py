"""DaData integration."""
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import logger


async def fetch_company_by_inn(inn: str) -> dict[str, Any] | None:
    """Fetch company details by INN."""
    if not settings.DADATA_TOKEN:
        return None
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"
    headers = {"Authorization": f"Token {settings.DADATA_TOKEN}"}
    payload = {"query": inn}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        suggestions = data.get("suggestions", [])
        return suggestions[0] if suggestions else None
    except httpx.HTTPError as exc:
        logger.exception("dadata_request_failed", error=str(exc))
        return None
    except ValueError as exc:
        logger.exception("dadata_invalid_response", error=str(exc))
        return None
