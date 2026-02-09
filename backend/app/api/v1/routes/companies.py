"""Company endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse

from app.api.v1.deps import get_current_user
from app.core.logging import logger
from app.db.models.company import Company
from app.db.models.company_api_keys import CompanyAPIKeys
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.company import CompanyCreate, CompanyOut, CompanyUpdate
from app.schemas.company_api_keys import CompanyAPIKeysOut, CompanyAPIKeysSet
from app.services.dadata import fetch_company_by_inn
from app.services.encryption import encrypt
from app.services.pdf import ContractData, render_contract_pdf

router = APIRouter()


@router.post("", response_model=CompanyOut)
async def create_company(
    payload: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyOut:
    """Create a company and optionally enrich via DaData."""
    company_data = await fetch_company_by_inn(payload.inn)
    name = payload.name or (company_data or {}).get("value") or payload.inn
    legal_form = payload.legal_form or (company_data or {}).get("data", {}).get("opf", {}).get("short")
    director = payload.director or (company_data or {}).get("data", {}).get("management", {}).get("name")

    company = Company(
        user_id=current_user.id,
        inn=payload.inn,
        name=name,
        legal_form=legal_form,
        director=director,
        bank_bik=payload.bank_bik,
        bank_account=payload.bank_account,
        contract_data=company_data,
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company


@router.get("", response_model=list[CompanyOut])
async def list_companies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CompanyOut]:
    """List companies for a user."""
    result = await db.execute(select(Company).where(Company.user_id == current_user.id))
    return list(result.scalars().all())


@router.patch("/{company_id}", response_model=CompanyOut)
async def update_company(
    company_id: int,
    payload: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyOut:
    """Update company details."""
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.user_id == current_user.id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Компания не найдена")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, key, value)
    await db.commit()
    await db.refresh(company)
    return company


@router.get("/{company_id}/contract")
async def generate_contract(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Generate a contract PDF."""
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.user_id == current_user.id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Компания не найдена")

    contract = ContractData(
        company_name=company.name,
        inn=company.inn,
        director=company.director,
        bank_bik=company.bank_bik,
        bank_account=company.bank_account,
    )
    try:
        pdf_bytes = render_contract_pdf(contract)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("contract_generation_failed", company_id=company_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Не удалось сформировать договор") from exc
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=contract.pdf"},
    )


async def _ensure_company_owner(company_id: int, current_user: User, db: AsyncSession) -> Company:
    """Return company if current user owns it; else raise 404."""
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.user_id == current_user.id)
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Компания не найдена")
    return company


@router.get("/{company_id}/api-keys", response_model=CompanyAPIKeysOut)
async def get_company_api_keys(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyAPIKeysOut:
    """Get masked API keys status (presence only)."""
    await _ensure_company_owner(company_id, current_user, db)
    result = await db.execute(select(CompanyAPIKeys).where(CompanyAPIKeys.company_id == company_id))
    row = result.scalar_one_or_none()
    if not row:
        return CompanyAPIKeysOut()
    return CompanyAPIKeysOut(
        has_wb=bool(row.wb_api_key_encrypted),
        has_ozon_client_id=bool(row.ozon_client_id_encrypted),
        has_ozon_api_key=bool(row.ozon_api_key_encrypted),
    )


def _encrypt_or_none(value: str | None) -> str | None:
    """Encrypt non-empty string; return None for empty. Raises HTTP 503 if ENCRYPTION_KEY not set."""
    if not value or not str(value).strip():
        return None
    try:
        return encrypt(str(value).strip())
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Шифрование не настроено (ENCRYPTION_KEY)",
        )


@router.put("/{company_id}/api-keys", response_model=CompanyAPIKeysOut)
async def set_company_api_keys(
    company_id: int,
    payload: CompanyAPIKeysSet,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyAPIKeysOut:
    """Set or update API keys (stored encrypted). Only non-empty fields are updated; omit field or send empty to leave unchanged."""
    await _ensure_company_owner(company_id, current_user, db)
    data = payload.model_dump(exclude_unset=True)

    result = await db.execute(select(CompanyAPIKeys).where(CompanyAPIKeys.company_id == company_id))
    row = result.scalar_one_or_none()
    if row:
        if "wb_api_key" in data and data["wb_api_key"] and str(data["wb_api_key"]).strip():
            row.wb_api_key_encrypted = _encrypt_or_none(data["wb_api_key"])
        if "ozon_client_id" in data and data["ozon_client_id"] and str(data["ozon_client_id"]).strip():
            row.ozon_client_id_encrypted = _encrypt_or_none(data["ozon_client_id"])
        if "ozon_api_key" in data and data["ozon_api_key"] and str(data["ozon_api_key"]).strip():
            row.ozon_api_key_encrypted = _encrypt_or_none(data["ozon_api_key"])
    else:
        wb_enc = _encrypt_or_none(payload.wb_api_key)
        ozon_client_enc = _encrypt_or_none(payload.ozon_client_id)
        ozon_key_enc = _encrypt_or_none(payload.ozon_api_key)
        row = CompanyAPIKeys(
            company_id=company_id,
            wb_api_key_encrypted=wb_enc,
            ozon_client_id_encrypted=ozon_client_enc,
            ozon_api_key_encrypted=ozon_key_enc,
        )
        db.add(row)
    await db.commit()
    await db.refresh(row)
    return CompanyAPIKeysOut(
        has_wb=bool(row.wb_api_key_encrypted),
        has_ozon_client_id=bool(row.ozon_client_id_encrypted),
        has_ozon_api_key=bool(row.ozon_api_key_encrypted),
    )


@router.delete("/{company_id}/api-keys", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company_api_keys(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove API keys for the company."""
    await _ensure_company_owner(company_id, current_user, db)
    await db.execute(delete(CompanyAPIKeys).where(CompanyAPIKeys.company_id == company_id))
    await db.commit()
