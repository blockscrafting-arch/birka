"""Company endpoints."""
import asyncio
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.company import Company
from app.db.models.contract_template import ContractTemplate
from app.db.session import get_db
from fastapi.responses import StreamingResponse

from app.api.v1.deps import get_current_user
from app.db.models.company_api_keys import CompanyAPIKeys
from app.db.models.user import User
from app.schemas.company import (
    CompanyAPIKeysOut,
    CompanyAPIKeysUpdate,
    CompanyCreate,
    CompanyList,
    CompanyOut,
    CompanyUpdate,
)
from app.schemas.company import _mask_key
from app.core.logging import logger
from app.services.contract_template_service import render_contract_pdf_from_docx_template
from app.services.dadata import fetch_bank_by_bik, fetch_company_by_inn
from app.services.pdf import ContractData, render_contract_pdf
from app.services.files import content_disposition
from app.services.s3 import S3Service
from app.services.telegram import send_document

router = APIRouter()


@router.get("/bank-by-bik")
async def bank_by_bik(
    bik: str = Query(..., min_length=1, max_length=20),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return bank name and correspondent account by BIK for autofill."""
    bik = bik.strip()
    if len(bik) != 9 or not bik.isdigit():
        raise HTTPException(status_code=422, detail="БИК должен быть 9 цифр")
    bank = await fetch_bank_by_bik(bik)
    if not bank:
        return {"bank_name": None, "bank_corr_account": None}
    data = bank.get("data", {})
    name_obj = data.get("name") or {}
    bank_name = name_obj.get("payment") or name_obj.get("full") or bank.get("value")
    bank_corr_account = data.get("correspondent_account")
    return {"bank_name": bank_name, "bank_corr_account": bank_corr_account}


@router.post("", response_model=CompanyOut)
async def create_company(
    payload: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyOut:
    """Create a company and optionally enrich via DaData."""
    company_data = await fetch_company_by_inn(payload.inn)
    data = (company_data or {}).get("data") or {}
    name = payload.name or (company_data or {}).get("value") or payload.inn
    legal_form = payload.legal_form or data.get("opf", {}).get("short")
    director = payload.director or data.get("management", {}).get("name")
    kpp = payload.kpp or data.get("kpp")
    ogrn = payload.ogrn or data.get("ogrn")
    addr = data.get("address") or {}
    legal_address = payload.legal_address or addr.get("unrestricted_value") or addr.get("value")
    okved = payload.okved or data.get("okved")
    okveds = data.get("okveds") or []
    okved_name = payload.okved_name or next(
        (o.get("name") for o in okveds if o.get("main")), None
    )

    company = Company(
        user_id=current_user.id,
        inn=payload.inn,
        name=name,
        legal_form=legal_form,
        director=director,
        bank_bik=payload.bank_bik,
        bank_account=payload.bank_account,
        kpp=kpp,
        ogrn=ogrn,
        legal_address=legal_address,
        okved=okved,
        okved_name=okved_name,
        bank_name=payload.bank_name,
        bank_corr_account=payload.bank_corr_account,
        contract_data=company_data,
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company


@router.get("", response_model=CompanyList)
async def list_companies(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyList:
    """List companies for a user with pagination."""
    if current_user.role in {"warehouse", "admin"}:
        base_query = select(Company)
    else:
        base_query = select(Company).where(Company.user_id == current_user.id)
    total_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = int(total_result.scalar_one())
    offset = (page - 1) * limit
    result = await db.execute(base_query.offset(offset).limit(limit))
    items = list(result.scalars().all())
    return CompanyList(items=items, total=total, page=page, limit=limit)


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

    try:
        pdf_bytes, filename = await _generate_contract_pdf_bytes(db, company)
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": content_disposition(filename)},
        )
    except RuntimeError as exc:
        if "Старый шаблон" in str(exc) or "PDF" in str(exc):
            logger.warning("contract_pdf_legacy_pdf", company_id=company_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Шаблон договора устарел. Администратор должен загрузить шаблон заново (DOCX или RTF).",
            ) from exc
        raise
    except Exception as exc:
        logger.exception("contract_pdf_failed", company_id=company_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Не удалось сформировать PDF договора")


async def _generate_contract_pdf_bytes(
    db: AsyncSession, company: Company
) -> tuple[bytes, str]:
    """Generate contract PDF bytes and filename. Shared by GET contract and POST contract/send."""
    contract_date = date.today().strftime("%d.%m.%Y")
    contract_number = f"{company.id}-{date.today().strftime('%Y%m%d')}"
    contract = ContractData(
        company_name=company.name,
        inn=company.inn,
        director=company.director,
        bank_bik=company.bank_bik,
        bank_account=company.bank_account,
        contract_number=contract_number,
        contract_date=contract_date,
        service_description="Оказание услуг фулфилмента и сопутствующих работ на условиях настоящего договора.",
        kpp=company.kpp,
        ogrn=company.ogrn,
        legal_address=company.legal_address,
        bank_name=company.bank_name,
        bank_corr_account=company.bank_corr_account,
    )
    template_result = await db.execute(
        select(ContractTemplate).where(ContractTemplate.is_default.is_(True))
    )
    template = template_result.scalar_one_or_none()
    if template and template.file_key:
        s3 = S3Service()
        pdf_bytes = await asyncio.to_thread(
            render_contract_pdf_from_docx_template,
            s3, template.file_key, template.file_type, template.docx_key, contract,
        )
    else:
        pdf_bytes = await asyncio.to_thread(
            render_contract_pdf,
            contract, template.html_content if template else None,
        )
    filename = f"Договор_{company.name}_{contract_date}.pdf"
    return pdf_bytes, filename


@router.post("/{company_id}/contract/send")
async def send_contract_to_telegram(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Generate contract PDF and send it to the user in the chat with the bot."""
    result = await db.execute(
        select(Company)
        .options(joinedload(Company.user))
        .where(Company.id == company_id)
    )
    company = result.unique().scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Компания не найдена")
    if current_user.role not in ("warehouse", "admin") and company.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к компании")

    telegram_id = company.user.telegram_id if company.user else None
    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось отправить файл: пользователь не привязан к Telegram.",
        )

    try:
        pdf_bytes, filename = await _generate_contract_pdf_bytes(db, company)
    except RuntimeError as exc:
        if "Старый шаблон" in str(exc) or "PDF" in str(exc):
            logger.warning("contract_pdf_legacy_pdf", company_id=company_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Шаблон договора устарел. Администратор должен загрузить шаблон заново (DOCX или RTF).",
            ) from exc
        raise
    except Exception as exc:
        logger.exception("contract_pdf_failed", company_id=company_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Не удалось сформировать PDF договора")

    sent = await send_document(telegram_id, pdf_bytes, filename, caption="Договор")
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Не удалось отправить файл в Telegram. Попробуйте позже.",
        )
    return {"sent": True}


def _company_access(company: Company, current_user: User) -> bool:
    """True if current_user can manage this company (owner or admin)."""
    return company.user_id == current_user.id or current_user.role == "admin"


@router.get("/{company_id}/api-keys", response_model=CompanyAPIKeysOut)
async def get_company_api_keys(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyAPIKeysOut:
    """Get API keys for company (masked). Only owner or admin."""
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Компания не найдена")
    if not _company_access(company, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к компании")

    result = await db.execute(
        select(CompanyAPIKeys).where(CompanyAPIKeys.company_id == company_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        return CompanyAPIKeysOut(
            company_id=company_id,
            wb_api_key=None,
            ozon_client_id=None,
            ozon_api_key=None,
        )
    secret = settings.ENCRYPTION_KEY or ""
    return CompanyAPIKeysOut(
        company_id=company_id,
        wb_api_key=_mask_key(decrypt_value(row.wb_api_key, secret)),
        ozon_client_id=_mask_key(decrypt_value(row.ozon_client_id, secret)),
        ozon_api_key=_mask_key(decrypt_value(row.ozon_api_key, secret)),
    )


@router.put("/{company_id}/api-keys", response_model=CompanyAPIKeysOut)
async def update_company_api_keys(
    company_id: int,
    payload: CompanyAPIKeysUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyAPIKeysOut:
    """Create or update API keys for company. Only owner or admin."""
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Компания не найдена")
    if not _company_access(company, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к компании")

    result = await db.execute(
        select(CompanyAPIKeys).where(CompanyAPIKeys.company_id == company_id)
    )
    row = result.scalar_one_or_none()
    data = payload.model_dump(exclude_unset=True)
    data = {k: (v if v else None) for k, v in data.items()}
    secret = settings.ENCRYPTION_KEY or ""

    if not row:
        row = CompanyAPIKeys(
            company_id=company_id,
            wb_api_key=encrypt_value(data.get("wb_api_key"), secret),
            ozon_client_id=encrypt_value(data.get("ozon_client_id"), secret),
            ozon_api_key=encrypt_value(data.get("ozon_api_key"), secret),
        )
        db.add(row)
    else:
        if "wb_api_key" in data:
            row.wb_api_key = encrypt_value(data["wb_api_key"], secret)
        if "ozon_client_id" in data:
            row.ozon_client_id = encrypt_value(data["ozon_client_id"], secret)
        if "ozon_api_key" in data:
            row.ozon_api_key = encrypt_value(data["ozon_api_key"], secret)
    await db.commit()
    await db.refresh(row)

    return CompanyAPIKeysOut(
        company_id=company_id,
        wb_api_key=_mask_key(decrypt_value(row.wb_api_key, secret)),
        ozon_client_id=_mask_key(decrypt_value(row.ozon_client_id, secret)),
        ozon_api_key=_mask_key(decrypt_value(row.ozon_api_key, secret)),
    )
