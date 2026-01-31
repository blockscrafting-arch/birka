"""Database session setup."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


engine = create_async_engine(settings.POSTGRES_DSN, echo=False, future=True)
AsyncSessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncSession:
    """Provide a database session."""
    async with AsyncSessionLocal() as session:
        yield session
