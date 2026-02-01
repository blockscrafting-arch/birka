"""API router."""
from fastapi import APIRouter

from app.api.v1.routes.ai import router as ai_router
from app.api.v1.routes.admin import router as admin_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.companies import router as companies_router
from app.api.v1.routes.destinations import router as destinations_router
from app.api.v1.routes.orders import router as orders_router
from app.api.v1.routes.products import router as products_router
from app.api.v1.routes.shipping import router as shipping_router
from app.api.v1.routes.warehouse import router as warehouse_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(companies_router, prefix="/companies", tags=["companies"])
api_router.include_router(destinations_router, prefix="/destinations", tags=["destinations"])
api_router.include_router(products_router, prefix="/products", tags=["products"])
api_router.include_router(orders_router, prefix="/orders", tags=["orders"])
api_router.include_router(shipping_router, prefix="/shipping", tags=["shipping"])
api_router.include_router(warehouse_router, prefix="/warehouse", tags=["warehouse"])
api_router.include_router(ai_router, prefix="/ai", tags=["ai"])
