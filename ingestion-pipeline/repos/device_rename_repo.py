# repos/device_rename_repo.py
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import DeviceRename
from schemas import DeviceRenameCreate

logger = logging.getLogger(__name__)


class DeviceRenameRepo:
    """Data access layer for DeviceRename records."""

    async def create(self, session: AsyncSession, data: DeviceRenameCreate, *, flush: bool = False) -> DeviceRename:
        logger.debug(f"Creating device rename with data: {data}")
        device_rename = DeviceRename(**data.model_dump(exclude_unset=True))
        session.add(device_rename)
        if flush:
            await session.flush()
        return device_rename

    async def get_all(self, session: AsyncSession) -> list[DeviceRename]:
        logger.debug("Fetching all device renames.")
        result = await session.execute(select(DeviceRename))
        return list(result.scalars().all())
