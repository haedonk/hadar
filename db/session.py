# db/session.py
import asyncio
import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import config

logger = logging.getLogger(__name__)

engine = create_async_engine(config.DATABASE_URL, echo=config.DEBUG)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def get_db(timeout: float = 5.0):
    """Async context manager for database sessions with timeout."""
    session = AsyncSessionLocal()
    try:
        try:
            yield await asyncio.wait_for(_session_yielder(session), timeout=timeout)
        except asyncio.TimeoutError:
            logger.error("Session timed out after %s seconds.", timeout)
            raise
    finally:
        await session.close()


async def _session_yielder(session: AsyncSession) -> AsyncSession:
    """Return the session after awaiting (used for timeout wrapping)."""
    return session
