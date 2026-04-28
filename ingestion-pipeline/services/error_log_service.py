# services/error_log_service.py
import logging
import traceback
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from db.session import get_db
from repos.error_log_repo import ErrorLogRepo
from schemas.error_log import ErrorLog, ErrorLogCreate

logger = logging.getLogger(__name__)


class ErrorLogService:
    def __init__(self):
        logger.debug("Initializing ErrorLogService.")
        self.error_log_repo = ErrorLogRepo()

    async def log_error(
        self,
        source: str,
        error_type: str,
        message: str,
        details: Optional[str] = None,
        device_id: Optional[UUID] = None,
        topic: Optional[str] = None,
    ) -> Optional[ErrorLog]:
        """
        Log an error to the database.

        Args:
            source: Source of the error (e.g., 'mqtt_ingest', 'zigbee2mqtt', 'api', 'batch_job')
            error_type: Type of error (e.g., 'parse_error', 'db_error', 'timeout')
            message: Human-readable error message
            details: Optional stack trace or raw payload
            device_id: Optional device UUID if error is device-specific
            topic: Optional MQTT topic if applicable

        Returns:
            ErrorLog object if successful, None otherwise
        """
        logger.debug(f"Logging error: source={source}, error_type={error_type}, message={message}")
        try:
            async with get_db() as session:
                error_data = ErrorLogCreate(
                    source=source,
                    error_type=error_type,
                    message=message,
                    details=details,
                    device_id=device_id,
                    topic=topic,
                )
                error_log = await self.error_log_repo.create(session, error_data, flush=True)
                await session.commit()
                logger.info(f"Error logged successfully with ID: {error_log.id}")
                return error_log
        except Exception as e:
            logger.error(f"Failed to log error to database: {e}", exc_info=True)
            return None

    async def log_exception(
        self,
        source: str,
        error_type: str,
        exception: Exception,
        device_id: Optional[UUID] = None,
        topic: Optional[str] = None,
        additional_context: Optional[str] = None,
    ) -> Optional[ErrorLog]:
        """
        Log an exception to the database with full stack trace.

        Args:
            source: Source of the error
            error_type: Type of error
            exception: The exception object
            device_id: Optional device UUID
            topic: Optional MQTT topic
            additional_context: Optional additional context to prepend to details

        Returns:
            ErrorLog object if successful, None otherwise
        """
        message = str(exception)
        stack_trace = traceback.format_exc()

        details_parts = []
        if additional_context:
            details_parts.append(f"Context: {additional_context}")
        details_parts.append(f"Exception: {exception.__class__.__name__}")
        details_parts.append(f"Stack Trace:\n{stack_trace}")

        details = "\n".join(details_parts)

        return await self.log_error(
            source=source,
            error_type=error_type,
            message=message,
            details=details,
            device_id=device_id,
            topic=topic,
        )

    async def bulk_log_errors(self, errors: List[ErrorLogCreate]) -> int:
        """
        Bulk insert error logs.

        Args:
            errors: List of ErrorLogCreate objects

        Returns:
            Number of errors logged
        """
        logger.debug(f"Bulk logging {len(errors)} errors.")
        try:
            async with get_db() as session:
                await self.error_log_repo.bulk_create(session, errors)
                await session.commit()
                logger.info(f"Successfully bulk logged {len(errors)} errors.")
                return len(errors)
        except Exception as e:
            logger.error(f"Failed to bulk log errors: {e}", exc_info=True)
            return 0

    async def get_error_by_id(self, error_log_id: int) -> Optional[ErrorLog]:
        """Get a specific error log by ID."""
        logger.debug(f"Fetching error log by ID: {error_log_id}")
        try:
            async with get_db() as session:
                return await self.error_log_repo.get_by_id(session, error_log_id)
        except Exception as e:
            logger.error(f"Error fetching error log {error_log_id}: {e}", exc_info=True)
            return None

    async def get_errors_by_source(self, source: str, limit: int = 100) -> List[ErrorLog]:
        """Get error logs by source."""
        logger.debug(f"Fetching error logs by source: {source}")
        try:
            async with get_db() as session:
                return await self.error_log_repo.get_by_source(session, source, limit)
        except Exception as e:
            logger.error(f"Error fetching error logs by source: {e}", exc_info=True)
            return []

    async def get_errors_by_type(self, error_type: str, limit: int = 100) -> List[ErrorLog]:
        """Get error logs by error type."""
        logger.debug(f"Fetching error logs by error_type: {error_type}")
        try:
            async with get_db() as session:
                return await self.error_log_repo.get_by_error_type(session, error_type, limit)
        except Exception as e:
            logger.error(f"Error fetching error logs by type: {e}", exc_info=True)
            return []

    async def get_errors_by_device(self, device_id: UUID, limit: int = 100) -> List[ErrorLog]:
        """Get error logs for a specific device."""
        logger.debug(f"Fetching error logs by device_id: {device_id}")
        try:
            async with get_db() as session:
                return await self.error_log_repo.get_by_device(session, device_id, limit)
        except Exception as e:
            logger.error(f"Error fetching error logs by device: {e}", exc_info=True)
            return []

    async def get_recent_errors(self, limit: int = 100) -> List[ErrorLog]:
        """Get most recent error logs."""
        logger.debug(f"Fetching recent error logs, limit: {limit}")
        try:
            async with get_db() as session:
                return await self.error_log_repo.get_recent(session, limit)
        except Exception as e:
            logger.error(f"Error fetching recent error logs: {e}", exc_info=True)
            return []

    async def get_errors_by_date_range(
        self, start_date: datetime, end_date: datetime, limit: int = 1000
    ) -> List[ErrorLog]:
        """Get error logs within a date range."""
        logger.debug(f"Fetching error logs from {start_date} to {end_date}")
        try:
            async with get_db() as session:
                return await self.error_log_repo.get_by_date_range(session, start_date, end_date, limit)
        except Exception as e:
            logger.error(f"Error fetching error logs by date range: {e}", exc_info=True)
            return []
