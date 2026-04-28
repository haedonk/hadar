# repos/temperature_repo.py
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import TemperatureReading
from schemas import TemperatureReadingCreate

logger = logging.getLogger(__name__)


class TemperatureRepo:
    """Data access layer for TemperatureReading records."""

    async def create(
        self, session: AsyncSession, data: TemperatureReadingCreate, *, flush: bool = False
    ) -> TemperatureReading:
        """Append a new temperature reading. Caller controls flush/commit."""
        logger.debug(f"Creating temperature reading with data: {data}")
        reading = TemperatureReading(**data.model_dump(exclude_unset=True))
        session.add(reading)
        if flush:
            await session.flush()
        return reading

    async def bulk_create(
        self, session: AsyncSession, data_list: list[TemperatureReadingCreate], *, flush: bool = False
    ) -> list[TemperatureReading]:
        """Append multiple new temperature readings. Caller controls flush/commit."""
        logger.debug(f"Bulk creating {len(data_list)} temperature readings.")
        readings = [TemperatureReading(**data.model_dump(exclude_unset=True)) for data in data_list]
        session.add_all(readings)
        if flush:
            await session.flush()
        return readings
