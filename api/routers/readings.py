from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_session
from queries import fetch_device_anomaly_events, fetch_device_readings
from schemas import DeviceAnomalyEventItem, EnergyReadingsResponse, StatusFilter, TemperatureReadingsResponse

router = APIRouter(prefix="/api/devices/{device_id}", tags=["device-readings"])


@router.get("/anomaly-events", response_model=list[DeviceAnomalyEventItem])
async def list_device_anomaly_events(
    device_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(gt=0, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: StatusFilter = "all",
    days: Annotated[int, Query(gt=0, le=3650)] = 30,
) -> list[dict]:
    events = await fetch_device_anomaly_events(
        session,
        device_id=device_id,
        limit=limit,
        offset=offset,
        status=status,
        days=days,
    )
    if events is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return events


@router.get("/readings", response_model=TemperatureReadingsResponse | EnergyReadingsResponse)
async def get_device_readings(
    device_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    days: Annotated[int, Query(gt=0, le=3650)] = 7,
    limit: Annotated[int, Query(gt=0, le=10000)] = 2000,
) -> dict:
    readings = await fetch_device_readings(session, device_id=device_id, days=days, limit=limit)
    if readings is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return readings
