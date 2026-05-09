from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_db() as session:
        yield session
