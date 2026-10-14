import os

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from app.config import get_settings

settings = get_settings()

database_url = make_url(settings.DATABASE_URL)
connect_args = {}
if "sslmode" in database_url.query:
    # asyncpg expects `ssl`, while Render's external URL uses `sslmode`.
    connect_args["ssl"] = database_url.query["sslmode"]
    database_url = database_url.difference_update_query(["sslmode"])

engine_options = {"poolclass": NullPool} if os.getenv("M6_SERVERLESS") == "true" else {}
engine = create_async_engine(
    database_url,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    connect_args=connect_args,
    **engine_options,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
