from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_session
from queries import fetch_summary
from schemas import Summary

router = APIRouter(prefix="/api/summary", tags=["summary"])


@router.get("", response_model=Summary)
async def get_summary(session: Annotated[AsyncSession, Depends(get_session)]) -> dict:
    return await fetch_summary(session, window_hours=24)
