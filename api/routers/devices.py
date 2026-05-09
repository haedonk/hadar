from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_session
from queries import fetch_device, fetch_devices
from schemas import DeviceStatus

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("", response_model=list[DeviceStatus])
async def list_devices(session: Annotated[AsyncSession, Depends(get_session)]) -> list[dict]:
    return await fetch_devices(session)


@router.get("/{device_id}", response_model=DeviceStatus)
async def get_device(device_id: UUID, session: Annotated[AsyncSession, Depends(get_session)]) -> dict:
    device = await fetch_device(session, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device
