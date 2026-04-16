"""Factory for WB/Ozon API clients using company API keys."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.company_api_keys import CompanyAPIKeys
from app.services.encryption import decrypt
from app.services.ozon_client import OzonClient
from app.services.wb_client import WBClient


async def get_wb_client(company_id: int, db: AsyncSession) -> WBClient:
    """Load WB API key for company, decrypt, return WBClient. Raises 400 if no key."""
    result = await db.execute(select(CompanyAPIKeys).where(CompanyAPIKeys.company_id == company_id))
    row = result.scalar_one_or_none()
    if not row or not row.wb_api_key_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API-ключ Wildberries не задан для компании",
        )
    try:
        api_key = decrypt(row.wb_api_key_encrypted)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось расшифровать ключ WB",
        )
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Шифрование не настроено (ENCRYPTION_KEY)",
        )
    return WBClient(api_key=api_key)


async def get_ozon_client(company_id: int, db: AsyncSession) -> OzonClient:
    """Load Ozon Client-Id and Api-Key for company, decrypt, return OzonClient. Raises 400 if missing."""
    result = await db.execute(select(CompanyAPIKeys).where(CompanyAPIKeys.company_id == company_id))
    row = result.scalar_one_or_none()
    if not row or not row.ozon_client_id_encrypted or not row.ozon_api_key_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API-ключи Ozon (Client-ID и Api-Key) не заданы для компании",
        )
    try:
        client_id = decrypt(row.ozon_client_id_encrypted)
        api_key = decrypt(row.ozon_api_key_encrypted)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось расшифровать ключи Ozon",
        )
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Шифрование не настроено (ENCRYPTION_KEY)",
        )
    return OzonClient(client_id=client_id, api_key=api_key)
