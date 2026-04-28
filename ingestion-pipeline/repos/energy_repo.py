# repos/energy_repo.py
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import EnergyReading
from schemas import EnergyReadingCreate

logger = logging.getLogger(__name__)


class EnergyRepo:
    """Data access layer for EnergyReading records."""

    async def create(self, session: AsyncSession, data: EnergyReadingCreate, *, flush: bool = False) -> EnergyReading:
        """Append a new energy reading. Caller controls flush/commit."""
        logger.debug(f"Creating energy reading with data: {data}")
        reading = EnergyReading(**data.model_dump(exclude_unset=True))
        session.add(reading)
        if flush:
            await session.flush()
        return reading

    async def bulk_create(
        self, session: AsyncSession, data_list: list[EnergyReadingCreate], *, flush: bool = False
    ) -> list[EnergyReading]:
        """Append multiple new energy readings. Caller controls flush/commit."""
        logger.debug(f"Bulk creating {len(data_list)} energy readings.")
        readings = [EnergyReading(**data.model_dump(exclude_unset=True)) for data in data_list]
        session.add_all(readings)
        if flush:
            await session.flush()
        return readings
