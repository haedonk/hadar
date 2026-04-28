# repos/error_log_repo.py
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ErrorLog
from schemas import ErrorLogCreate, ErrorLogUpdate

logger = logging.getLogger(__name__)


class ErrorLogRepo:
    """Data access layer for ErrorLog records."""

    async def create(self, session: AsyncSession, data: ErrorLogCreate, *, flush: bool = False) -> ErrorLog:
        """Create a new error log entry. Caller controls flush/commit."""
        logger.debug(f"Creating error log with data: {data}")
        error_log = ErrorLog(**data.model_dump(exclude_unset=True))
        session.add(error_log)
        if flush:
            await session.flush()
        return error_log

    async def bulk_create(
        self, session: AsyncSession, data_list: List[ErrorLogCreate], *, flush: bool = False
    ) -> List[ErrorLog]:
        """Create multiple error log entries. Caller controls flush/commit."""
        logger.debug(f"Bulk creating {len(data_list)} error logs.")
        error_logs = [ErrorLog(**data.model_dump(exclude_unset=True)) for data in data_list]
        session.add_all(error_logs)
        if flush:
            await session.flush()
        return error_logs

    async def get_by_id(self, session: AsyncSession, error_log_id: int) -> Optional[ErrorLog]:
        logger.debug(f"Fetching error log by id: {error_log_id}")
        result = await session.execute(select(ErrorLog).where(ErrorLog.id == error_log_id))
        return result.scalars().first()

    async def get_by_source(self, session: AsyncSession, source: str, limit: int = 100) -> List[ErrorLog]:
        logger.debug(f"Fetching error logs by source: {source}, limit: {limit}")
        result = await session.execute(
            select(ErrorLog).where(ErrorLog.source == source).order_by(desc(ErrorLog.created_at)).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_error_type(self, session: AsyncSession, error_type: str, limit: int = 100) -> List[ErrorLog]:
        logger.debug(f"Fetching error logs by error_type: {error_type}, limit: {limit}")
        result = await session.execute(
            select(ErrorLog).where(ErrorLog.error_type == error_type).order_by(desc(ErrorLog.created_at)).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_device(self, session: AsyncSession, device_id: UUID, limit: int = 100) -> List[ErrorLog]:
        logger.debug(f"Fetching error logs by device_id: {device_id}, limit: {limit}")
        result = await session.execute(
            select(ErrorLog).where(ErrorLog.device_id == device_id).order_by(desc(ErrorLog.created_at)).limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent(self, session: AsyncSession, limit: int = 100) -> List[ErrorLog]:
        logger.debug(f"Fetching recent error logs, limit: {limit}")
        result = await session.execute(select(ErrorLog).order_by(desc(ErrorLog.created_at)).limit(limit))
        return list(result.scalars().all())

    async def get_by_date_range(
        self, session: AsyncSession, start_date: datetime, end_date: datetime, limit: int = 1000
    ) -> List[ErrorLog]:
        logger.debug(f"Fetching error logs from {start_date} to {end_date}, limit: {limit}")
        result = await session.execute(
            select(ErrorLog)
            .where(ErrorLog.created_at >= start_date)
            .where(ErrorLog.created_at <= end_date)
            .order_by(desc(ErrorLog.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update(
        self, session: AsyncSession, error_log: ErrorLog, data: ErrorLogUpdate, *, flush: bool = False
    ) -> ErrorLog:
        logger.debug(f"Updating error log {error_log.id} with data: {data}")
        error_log = await session.merge(error_log)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(error_log, field, value)
        if flush:
            await session.flush()
        return error_log

    async def delete(self, session: AsyncSession, error_log: ErrorLog, *, flush: bool = False) -> None:
        logger.debug(f"Deleting error log {error_log.id}")
        await session.delete(error_log)
        if flush:
            await session.flush()
