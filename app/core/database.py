"""PostgreSQL 연결"""
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# URL 변환 (postgresql -> postgresql+asyncpg)
DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    """DB 세션 의존성"""
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def get_db_context():
    """DB 세션 컨텍스트 매니저 (이벤트 핸들러 등에서 사용)"""
    async with AsyncSessionLocal() as session:
        yield session