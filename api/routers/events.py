from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_session
from queries import fetch_anomaly_events
from schemas import AnomalyEventPage, Severity, StatusFilter

router = APIRouter(prefix="/api/anomaly-events", tags=["anomaly-events"])


@router.get("", response_model=AnomalyEventPage)
async def list_anomaly_events(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(gt=0, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: StatusFilter = "open",
    severity: Severity | None = None,
    hours: Annotated[int, Query(gt=0, le=8760)] = 24,
) -> dict:
    return await fetch_anomaly_events(
        session,
        limit=limit,
        offset=offset,
        status=status,
        severity=severity,
        hours=hours,
    )
