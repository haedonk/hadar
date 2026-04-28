import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from schemas.energy_reading import EnergyReadingCreate

logger = logging.getLogger(__name__)


def get_energy_reading(
    device_id: UUID,
    ts: datetime,
    load_group_id: Optional[UUID] = None,
    power_watts: Optional[Decimal] = None,
    energy_kwh: Optional[Decimal] = None,
    voltage_volts: Optional[Decimal] = None,
    current_amps: Optional[Decimal] = None,
    power_factor: Optional[Decimal] = None,
    linkquality: Optional[int] = None,
    source: str = "zigbee2mqtt",
) -> EnergyReadingCreate:
    """Create an EnergyReadingCreate schema with sensible defaults."""
    logger.debug(f"Creating energy reading for device_id={device_id}, load_group_id={load_group_id}")
    return EnergyReadingCreate(
        device_id=device_id,
        load_group_id=load_group_id,
        ts=ts,
        power_watts=power_watts,
        energy_kwh=energy_kwh,
        voltage_volts=voltage_volts,
        current_amps=current_amps,
        power_factor=power_factor,
        linkquality=linkquality,
        source=source,
    )
