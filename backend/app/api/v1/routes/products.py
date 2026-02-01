"""Product endpoints."""
from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.models.company import Company
from app.db.models.product import Product, ProductPhoto
from app.db.session import get_db
from app.schemas.product import ProductCreate, ProductList, ProductOut, ProductUpdate
from app.services.excel import export_products, parse_products_excel
from app.services.pdf import LabelData, render_label_pdf
from app.services.s3 import S3Service
from app.core.config import settings
from app.db.models.user import User

router = APIRouter()


@router.post("", response_model=ProductOut)
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductOut:
    """Create product."""
    company_result = await db.execute(
        select(Company).where(Company.id == payload.company_id, Company.user_id == current_user.id)
    )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Company not found")
    product = Product(**payload.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.get("", response_model=ProductList)
async def list_products(
    company_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductList:
    """List products by company with pagination."""
    company_result = await db.execute(
        select(Company).where(Company.id == company_id, Company.user_id == current_user.id)
    )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Company not found")
    base_query = select(Product).where(Product.company_id == company_id)
    total_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = int(total_result.scalar_one())
    offset = (page - 1) * limit
    result = await db.execute(base_query.offset(offset).limit(limit))
    items = list(result.scalars().all())
    return ProductList(items=items, total=total, page=page, limit=limit)


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductOut:
    """Update product."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    company_result = await db.execute(
        select(Company).where(Company.id == product.company_id, Company.user_id == current_user.id)
    )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Company not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    await db.commit()
    await db.refresh(product)
    return product


@router.post("/import")
async def import_products(
    company_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Import products from Excel."""
    if file.content_type not in {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    }:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    company_result = await db.execute(
        select(Company).where(Company.id == company_id, Company.user_id == current_user.id)
    )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Company not found")
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large")
    parsed = parse_products_excel(data)
    created = 0
    for row in parsed:
        if not row.get("name"):
            continue
        product = Product(company_id=company_id, **row)
        db.add(product)
        created += 1
    await db.commit()
    return {"imported": created}


@router.get("/export")
async def export_products_excel(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Export products to Excel."""
    company_result = await db.execute(
        select(Company).where(Company.id == company_id, Company.user_id == current_user.id)
    )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Company not found")
    result = await db.execute(select(Product).where(Product.company_id == company_id))
    buffer = export_products(list(result.scalars().all()))
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=products.xlsx"},
    )


@router.post("/{product_id}/photo")
async def upload_product_photo(
    product_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Upload product photo to S3."""
    s3 = S3Service()
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Unsupported file type")
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large")
    image = Image.open(BytesIO(data))
    image.thumbnail((1200, 1200))
    output = BytesIO()
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    image.save(output, format="JPEG")
    data = output.getvalue()
    key = f"products/{product_id}/{datetime.utcnow().timestamp()}_{file.filename}"
    s3.upload_bytes(key, data, file.content_type or "image/jpeg")
    url = s3.build_public_url(key)
    if not await s3.head_check(url):
        raise HTTPException(status_code=400, detail="Upload verification failed")

    product_result = await db.execute(select(Product).where(Product.id == product_id))
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    company_result = await db.execute(
        select(Company).where(Company.id == product.company_id, Company.user_id == current_user.id)
    )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Company not found")

    photo = ProductPhoto(product_id=product_id, s3_key=key)
    db.add(photo)
    await db.commit()
    return {"key": key}


@router.get("/{product_id}/label")
async def generate_label(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Generate label PDF."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    company_result = await db.execute(
        select(Company).where(Company.id == product.company_id, Company.user_id == current_user.id)
    )
    company = company_result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    title_parts = [product.name, product.brand, product.size, product.color]
    title = " ".join([part for part in title_parts if part])
    label = LabelData(
        title=title,
        article=product.wb_article or "-",
        supplier=company.name,
        barcode_value=product.barcode or "-",
    )
    pdf_bytes = render_label_pdf(label)
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=label.pdf"},
    )
