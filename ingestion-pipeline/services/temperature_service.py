# services/temperature_service.py
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from config import Config
from db.session import get_db
from repos.temperature_repo import TemperatureRepo
from schemas.temperature_reading import TemperatureReadingCreate
from services.event_queue import TemperatureEventQueue
from utils.temperature_reading_utils import get_temperature_reading

logger = logging.getLogger(__name__)


class TemperatureService:
    def __init__(self):
        logger.debug("Initializing TemperatureService.")
        self.temperature_repo = TemperatureRepo()
        self.temperature_event_queue = TemperatureEventQueue(int(Config.QUEUE_MAX_COMMIT_SIZE / 2))
        # Lazy import to avoid circular dependency
        self._error_log_service = None

    def _get_error_log_service(self):
        """Lazy load error log service to avoid circular imports."""
        if self._error_log_service is None:
            from services.error_log_service import ErrorLogService

            self._error_log_service = ErrorLogService()
        return self._error_log_service

    async def add_temperature_event(self, event: Dict[str, Any]) -> None:
        """Add a temperature event to the queue."""
        event["ts"] = datetime.now(timezone(timedelta(hours=-5)))
        await self.temperature_event_queue.add_event(event)
        logger.debug("Number of events in temperature queue: %d", self.temperature_event_queue.queue.qsize())

    def is_queue_full(self) -> bool:
        """Check if the temperature event queue is full."""
        return self.temperature_event_queue.is_full()

    def is_queue_empty(self) -> bool:
        """Check if the temperature event queue is empty."""
        return self.temperature_event_queue.is_empty()

    async def process_temperature_events(self, get_device_id_func) -> int:
        """
        Process all temperature events in the queue and commit to database.

        Args:
            get_device_id_func: Async function to get/create device ID from friendly name and description

        Returns:
            Number of events processed
        """
        try:
            if not self.temperature_event_queue.is_full():
                return 0

            logger.info("Temperature event queue is full. Processing all events.")
            events = []

            while not self.temperature_event_queue.is_empty():
                evt = await self.temperature_event_queue.get_event()
                payload = evt.get("payload", {})
                friendly_name = evt.get("friendly_name")
                description = evt.get("definition", {}).get("description", "")

                # Get or create device ID
                device_id = await get_device_id_func(friendly_name, description)

                # Create temperature reading
                temperature_reading = get_temperature_reading(
                    device_id=device_id,
                    ts=evt.get("ts"),
                    battery=payload.get("battery"),
                    humidity=payload.get("humidity"),
                    pressure=payload.get("pressure"),
                    temperature=payload.get("temperature"),
                    linkquality=payload.get("linkquality"),
                )
                events.append(temperature_reading)
                self.temperature_event_queue.queue.task_done()

            # Bulk create all temperature readings
            async with get_db() as session:
                await self.temperature_repo.bulk_create(session, events)
                await session.commit()

            logger.info("Processed and committed %d temperature events to database.", len(events))
            return len(events)

        except Exception as e:
            logger.error(f"Error processing temperature events: {e}", exc_info=True)
            await self._get_error_log_service().log_exception(
                source="temperature_service",
                error_type="processing_error",
                exception=e,
                additional_context="Failed to process temperature events from queue",
            )
            return 0

    async def create_temperature_reading(
        self,
        device_id: UUID,
        ts: Optional[datetime] = None,
        battery: Optional[float] = None,
        humidity: Optional[float] = None,
        pressure: Optional[float] = None,
        temperature: Optional[float] = None,
        linkquality: Optional[int] = None,
    ) -> TemperatureReadingCreate:
        """
        Create a temperature reading object.

        Args:
            device_id: Device UUID
            ts: Timestamp (defaults to now if not provided)
            battery: Battery level
            humidity: Humidity percentage
            pressure: Atmospheric pressure
            temperature: Temperature
            linkquality: Link quality

        Returns:
            TemperatureReadingCreate schema object
        """
        if ts is None:
            ts = datetime.now(timezone(timedelta(hours=-5)))
        return get_temperature_reading(
            device_id=device_id,
            ts=ts,
            battery=battery,
            humidity=humidity,
            pressure=pressure,
            temperature=temperature,
            linkquality=linkquality,
        )

    async def bulk_create_temperature_readings(self, temperature_readings: List[TemperatureReadingCreate]) -> None:
        """
        Bulk create temperature readings in the database.

        Args:
            temperature_readings: List of TemperatureReadingCreate objects
        """
        try:
            async with get_db() as session:
                await self.temperature_repo.bulk_create(session, temperature_readings)
                await session.commit()
            logger.info("Bulk created %d temperature readings.", len(temperature_readings))
        except Exception as e:
            logger.error(f"Error bulk creating temperature readings: {e}", exc_info=True)
            await self._get_error_log_service().log_exception(
                source="temperature_service",
                error_type="db_error",
                exception=e,
                additional_context=f"Failed to bulk create {len(temperature_readings)} temperature readings",
            )
