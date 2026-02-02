"""Company endpoints."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.company import Company
from app.db.models.contract_template import ContractTemplate
from app.db.session import get_db
from fastapi.responses import StreamingResponse

from app.api.v1.deps import get_current_user
from app.db.models.user import User
from app.schemas.company import CompanyCreate, CompanyList, CompanyOut, CompanyUpdate
from app.core.logging import logger
from app.services.dadata import fetch_company_by_inn
from app.services.pdf import ContractData, render_contract_pdf
from app.services.files import content_disposition

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

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
    )
    try:
        template_result = await db.execute(
            select(ContractTemplate).where(ContractTemplate.is_default.is_(True))
        )
        template = template_result.scalar_one_or_none()
        pdf_bytes = render_contract_pdf(contract, template.html_content if template else None)
        filename = f"Договор_{company.name}_{contract_date}.pdf"
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": content_disposition(filename)},
        )
    except Exception as exc:
        logger.exception("contract_pdf_failed", company_id=company_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Contract PDF generation failed")
