from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from .settings import main_db


async def get_main_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with main_db() as session:
        yield session
