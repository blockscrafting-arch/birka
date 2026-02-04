"""Product endpoints."""
from datetime import date, datetime
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from PIL import Image
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.v1.deps import get_current_user
from app.db.models.company import Company
from app.db.models.order_photo import OrderPhoto
from app.db.models.product import Product, ProductPhoto
from app.db.session import get_db
from app.schemas.product import ImportResult, ImportSkipped, ProductCreate, ProductList, ProductOut, ProductUpdate
from app.services.excel import export_products, export_products_template, parse_products_excel
from app.services.files import content_disposition
from app.services.pdf import LabelData, render_label_pdf
from app.services.s3 import S3Service
from app.core.config import settings
from app.core.logging import logger
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
        raise HTTPException(status_code=404, detail="Компания не найдена")
    product = Product(**payload.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.get("", response_model=ProductList)
async def list_products(
    company_id: int,
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductList:
    """List products by company with pagination."""
    if current_user.role in {"warehouse", "admin"}:
        company_result = await db.execute(select(Company).where(Company.id == company_id))
    else:
        company_result = await db.execute(
            select(Company).where(Company.id == company_id, Company.user_id == current_user.id)
        )
    company = company_result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    base_query = select(Product).where(Product.company_id == company_id)
    if search:
        term = f"%{search.strip()}%"
        base_query = base_query.where(
            or_(
                Product.name.ilike(term),
                Product.barcode.ilike(term),
                Product.wb_article.ilike(term),
            )
        )
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
        raise HTTPException(status_code=404, detail="Товар не найден")
    if current_user.role in {"warehouse", "admin"}:
        company_result = await db.execute(select(Company).where(Company.id == product.company_id))
    else:
        company_result = await db.execute(
            select(Company).where(Company.id == product.company_id, Company.user_id == current_user.id)
        )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Компания не найдена")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    await db.commit()
    await db.refresh(product)
    return product


@router.post("/import", response_model=ImportResult)
async def import_products(
    company_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImportResult:
    """Import products from Excel."""
    if file.content_type not in {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    }:
        raise HTTPException(status_code=400, detail="Неподдерживаемый тип файла")
    company_result = await db.execute(
        select(Company).where(Company.id == company_id, Company.user_id == current_user.id)
    )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Компания не найдена")
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Файл слишком большой")
    try:
        parsed = parse_products_excel(data)
        created = 0
        updated = 0
        skipped: list[ImportSkipped] = []
        for row in parsed:
            if not row.get("name"):
                continue
            barcode = (row.get("barcode") or "").strip() or None
            if barcode:
                existing_result = await db.execute(
                    select(Product).where(Product.barcode == barcode)
                )
                existing = existing_result.scalar_one_or_none()
                if existing:
                    if existing.company_id == company_id:
                        for key, value in row.items():
                            if key == "company_id":
                                continue
                            if value is not None and hasattr(existing, key):
                                setattr(existing, key, value)
                        updated += 1
                    else:
                        skipped.append(
                            ImportSkipped(
                                barcode=barcode,
                                name=(row.get("name") or "").strip() or "-",
                                reason="ШК принадлежит другой компании",
                            )
                        )
                    continue
            product = Product(company_id=company_id, **row)
            db.add(product)
            created += 1
        await db.commit()
        return ImportResult(imported=created, updated=updated, skipped=skipped)
    except Exception as exc:
        await db.rollback()
        logger.exception("product_import_failed", company_id=company_id, error=str(exc))
        detail = str(exc) if isinstance(exc, ValueError) else "Product import failed"
        raise HTTPException(status_code=400, detail=detail)


@router.get("/export")
async def export_products_excel(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Export products to Excel."""
    if current_user.role in {"warehouse", "admin"}:
        company_result = await db.execute(select(Company).where(Company.id == company_id))
    else:
        company_result = await db.execute(
            select(Company).where(Company.id == company_id, Company.user_id == current_user.id)
        )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Компания не найдена")
    try:
        company = company_result.scalar_one_or_none()
        result = await db.execute(
            select(Product)
            .options(joinedload(Product.company))
            .where(Product.company_id == company_id)
        )
        products = list(result.unique().scalars().all())
        if not products:
            raise HTTPException(status_code=400, detail="Нет товаров для экспорта")
        buffer = export_products(products)
        filename = f"Товары_{company.name}_{date.today().strftime('%d.%m.%Y')}.xlsx"
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": content_disposition(filename)},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("product_export_failed", company_id=company_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Не удалось экспортировать товары")


@router.get("/template")
async def export_products_template_excel(
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Export products Excel template."""
    try:
        _ = current_user
        buffer = export_products_template()
        filename = "Шаблон_импорта_товаров.xlsx"
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": content_disposition(filename)},
        )
    except Exception as exc:
        logger.exception("product_template_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Не удалось выгрузить шаблон")


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
        raise HTTPException(status_code=400, detail="Неподдерживаемый тип файла")
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Файл слишком большой")
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
        raise HTTPException(status_code=400, detail="Ошибка проверки загруженного файла")

    product_result = await db.execute(select(Product).where(Product.id == product_id))
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    if current_user.role in {"warehouse", "admin"}:
        company_result = await db.execute(select(Company).where(Company.id == product.company_id))
    else:
        company_result = await db.execute(
            select(Company).where(Company.id == product.company_id, Company.user_id == current_user.id)
        )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Компания не найдена")

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
        raise HTTPException(status_code=404, detail="Товар не найден")
    company_result = await db.execute(
        select(Company).where(Company.id == product.company_id, Company.user_id == current_user.id)
    )
    company = company_result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Компания не найдена")

    if not product.name or not product.barcode or not product.wb_article:
        raise HTTPException(status_code=400, detail="Не заполнены обязательные поля для этикетки")
    supplier_name = product.supplier_name or company.name
    if not supplier_name:
        raise HTTPException(status_code=400, detail="Укажите поставщика для этикетки")

    title = product.name.strip()
    if product.size and product.size.strip():
        title = f"{title}, размер {product.size.strip()}"
    label = LabelData(
        title=title,
        article=product.wb_article or "-",
        supplier=supplier_name,
        barcode_value=product.barcode or "-",
    )
    pdf_bytes = render_label_pdf(label)
    filename = f"Этикетка_{product.name}_{product.barcode}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": content_disposition(filename)},
    )


@router.get("/{product_id}/defect-photos", response_model=list[str])
async def list_defect_photos(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[str]:
    """List defect photo URLs for a product."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    if current_user.role in {"warehouse", "admin"}:
        company_result = await db.execute(select(Company).where(Company.id == product.company_id))
    else:
        company_result = await db.execute(
            select(Company).where(Company.id == product.company_id, Company.user_id == current_user.id)
        )
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Компания не найдена")
    result = await db.execute(
        select(OrderPhoto).where(OrderPhoto.product_id == product_id, OrderPhoto.photo_type == "defect")
    )
    s3 = S3Service()
    return [s3.build_public_url(photo.s3_key) for photo in result.scalars().all()]
