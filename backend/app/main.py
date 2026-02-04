"""FastAPI application entrypoint. See project docs in /docs."""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import configure_logging, logger
from app.db.models.user import User
from app.db.session import get_db, AsyncSessionLocal


async def sync_roles_on_startup() -> None:
    """Выставить роль admin пользователям из ADMIN_TELEGRAM_IDS. Роль warehouse задаётся только вручную в админке."""
    if not settings.admin_telegram_ids:
        return
    admin_ids = set(settings.admin_telegram_ids)
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.telegram_id.in_(admin_ids)))
        users = result.scalars().all()
        updated = 0
        for user in users:
            if user.role != "admin":
                user.role = "admin"
                updated += 1
        if updated:
            await db.commit()
            logger.info("roles_synced_on_startup", updated=updated)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    if not settings.admin_telegram_ids:
        logger.warning("ADMIN_TELEGRAM_IDS_empty", detail="Задайте ADMIN_TELEGRAM_IDS в .env для доступа в админку")
    else:
        await sync_roles_on_startup()
    logger.info("app_initialized")
    yield
    # shutdown (nothing to do)


def create_app() -> FastAPI:
    """Create and configure the FastAPI app."""
    configure_logging()
    app = FastAPI(title="Birka API", version="0.1.0", lifespan=lifespan)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-Telegram-Init-Data", "X-Session-Token"],
    )

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/api", tags=["meta"])
    @app.get("/api/", tags=["meta"])
    async def api_root() -> dict:
        """Корень API: использовать /api/v1/..."""
        return {"message": "Use /api/v1/ for API endpoints"}

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Log unhandled exceptions."""
        logger.exception("unhandled_exception", path=request.url.path, error=str(exc))
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Log handled HTTP errors."""
        logger.warning("http_exception", path=request.url.path, status=exc.status_code, detail=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.get("/health", tags=["health"])
    async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
        """Simple health check endpoint."""
        try:
            await db.execute(text("SELECT 1"))
            return {"status": "ok", "db": "connected"}
        except Exception as exc:
            logger.exception("db_health_failed", error=str(exc))
            return {"status": "degraded", "db": "disconnected"}

    return app


app = create_app()
