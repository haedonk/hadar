# utils/temperature_reading_utils.py
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from schemas.temperature_reading import TemperatureReadingCreate

logger = logging.getLogger(__name__)


def get_temperature_reading(
    device_id: UUID,
    ts: datetime,
    battery: Optional[Decimal] = None,
    humidity: Optional[Decimal] = None,
    pressure: Optional[Decimal] = None,
    temperature: Optional[Decimal] = None,
    linkquality: Optional[int] = None,
    source: str = "zigbee2mqtt",
) -> TemperatureReadingCreate:
    """Create a TemperatureReadingCreate schema with sensible defaults."""
    logger.debug(f"Creating temperature reading for device_id={device_id}")
    return TemperatureReadingCreate(
        device_id=device_id,
        ts=ts,
        battery=battery,
        humidity=humidity,
        pressure=pressure,
        temperature=temperature,
        linkquality=linkquality,
        source=source,
    )
