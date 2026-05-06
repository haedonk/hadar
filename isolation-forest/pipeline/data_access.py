import pandas as pd
from sqlalchemy import select

from db import Device, TemperatureReading, get_db


async def fetch_temperature_readings() -> list[dict]:
    """Fetch all temperature readings joined with device labels."""
    async with get_db() as session:
        stmt = (
            select(
                TemperatureReading.id,
                Device.device_label,
                TemperatureReading.temperature,
                TemperatureReading.ts.label("datetime"),
            )
            .join(Device, Device.id == TemperatureReading.device_id)
            .order_by(Device.device_label, TemperatureReading.ts, TemperatureReading.id)
        )
        result = await session.execute(stmt)
        return [row._asdict() for row in result]


async def fetch_temperature_readings_df() -> pd.DataFrame:
    """Fetch all temperature readings as a DataFrame."""
    return pd.DataFrame(await fetch_temperature_readings())
