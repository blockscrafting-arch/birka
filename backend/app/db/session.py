"""Database session setup."""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


engine = create_async_engine(
    settings.POSTGRES_DSN,
    echo=False,
    future=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
)
AsyncSessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=AsyncSession,
)


def _sync_postgres_dsn() -> str:
    """DSN for sync engine (psycopg2). POSTGRES_DSN is postgresql+asyncpg://..."""
    dsn = settings.POSTGRES_DSN
    if "+asyncpg" in dsn:
        return dsn.replace("+asyncpg", "+psycopg2", 1)
    if dsn.startswith("postgresql://"):
        return dsn.replace("postgresql://", "postgresql+psycopg2://", 1)
    return dsn


sync_engine = create_engine(_sync_postgres_dsn(), echo=False, future=True)
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)


async def get_db() -> AsyncSession:
    """Provide a database session."""
    async with AsyncSessionLocal() as session:
        yield session
