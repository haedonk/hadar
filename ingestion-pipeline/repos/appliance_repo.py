import logging

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Appliance
from schemas import ApplianceCreate, ApplianceUpdate

logger = logging.getLogger(__name__)


class ApplianceRepo:
    """Data access layer for Appliance records."""

    async def create(self, session: AsyncSession, data: ApplianceCreate, *, flush: bool = False) -> Appliance:
        logger.debug(f"Creating appliance with data: {data}")
        appliance = Appliance(**data.model_dump(exclude_unset=True))
        session.add(appliance)
        if flush:
            await session.flush()
        return appliance

    async def update(
        self, session: AsyncSession, appliance: Appliance, data: ApplianceUpdate, *, flush: bool = False
    ) -> Appliance:
        logger.debug(f"Updating appliance {appliance} with data: {data}")
        appliance = await session.merge(appliance)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(appliance, field, value)
        if flush:
            await session.flush()
        return appliance

    async def delete(self, session: AsyncSession, appliance: Appliance, *, flush: bool = False) -> None:
        logger.debug(f"Deleting appliance: {appliance}")
        appliance = await session.merge(appliance)
        await session.delete(appliance)
        if flush:
            await session.flush()
