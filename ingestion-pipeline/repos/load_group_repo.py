import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import LoadGroup
from schemas import LoadGroupCreate, LoadGroupUpdate

logger = logging.getLogger(__name__)


class LoadGroupRepo:
    """Data access layer for LoadGroup records."""

    async def create(self, session: AsyncSession, data: LoadGroupCreate, *, flush: bool = False) -> LoadGroup:
        logger.debug(f"Creating load group with data: {data}")
        load_group = LoadGroup(**data.model_dump(exclude_unset=True))
        session.add(load_group)
        if flush:
            await session.flush()
        return load_group

    async def update(
        self, session: AsyncSession, load_group: LoadGroup, data: LoadGroupUpdate, *, flush: bool = False
    ) -> LoadGroup:
        logger.debug(f"Updating load group {load_group} with data: {data}")
        load_group = await session.merge(load_group)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(load_group, field, value)
        if flush:
            await session.flush()
        return load_group

    async def delete(self, session: AsyncSession, load_group: LoadGroup, *, flush: bool = False) -> None:
        logger.debug(f"Deleting load group: {load_group}")
        load_group = await session.merge(load_group)
        await session.delete(load_group)
        if flush:
            await session.flush()

    async def get_load_groups(self, session: AsyncSession) -> list[LoadGroup]:
        logger.debug("Fetching all load groups.")
        result = await session.execute(select(LoadGroup))
        return list(result.scalars().all())
