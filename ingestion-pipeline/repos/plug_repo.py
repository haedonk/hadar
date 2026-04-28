import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Device
from schemas import PlugCreate, PlugUpdate

logger = logging.getLogger(__name__)


class PlugRepo:
    """Data access layer for plug (Device) records."""

    async def create(self, session: AsyncSession, data: PlugCreate, *, flush: bool = False) -> Device:
        logger.debug(f"Creating plug with data: {data}")
        plug = Device(**data.model_dump(exclude_unset=True))
        session.add(plug)
        if flush:
            await session.flush()
        return plug

    async def update(self, session: AsyncSession, plug: Device, data: PlugUpdate, *, flush: bool = False) -> Device:
        logger.debug(f"Updating plug {plug} with data: {data}")
        plug = await session.merge(plug)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(plug, field, value)
        if flush:
            await session.flush()
        return plug

    async def delete(self, session: AsyncSession, plug: Device, *, flush: bool = False) -> None:
        logger.debug(f"Deleting plug: {plug}")
        plug = await session.merge(plug)
        await session.delete(plug)
        if flush:
            await session.flush()

    async def get_plugs(self, session: AsyncSession) -> list[Device]:
        logger.debug("Fetching all plugs.")
        result = await session.execute(select(Device))
        return list(result.scalars().all())
