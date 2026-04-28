import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Device
from schemas import DeviceCreate, DeviceUpdate

logger = logging.getLogger(__name__)


class DeviceRepo:
    """Data access layer for Device records."""

    async def create(self, session: AsyncSession, data: DeviceCreate, *, flush: bool = False) -> Device:
        logger.debug(f"Creating device with data: {data}")
        device = Device(**data.model_dump(exclude_unset=True))
        session.add(device)
        if flush:
            await session.flush()
        return device

    async def update(self, session: AsyncSession, device: Device, data: DeviceUpdate, *, flush: bool = False) -> Device:
        logger.debug(f"Updating device {device} with data: {data}")
        device = await session.merge(device)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(device, field, value)
        if flush:
            await session.flush()
        return device

    async def delete(self, session: AsyncSession, device: Device, *, flush: bool = False) -> None:
        logger.debug(f"Deleting device: {device}")
        device = await session.merge(device)
        await session.delete(device)
        if flush:
            await session.flush()

    async def get_devices(self, session: AsyncSession) -> list[Device]:
        logger.debug("Fetching all devices.")
        result = await session.execute(select(Device))
        return list(result.scalars().all())
