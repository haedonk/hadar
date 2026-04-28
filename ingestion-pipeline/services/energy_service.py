import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from config import Config
from db.session import get_db
from repos.energy_repo import EnergyRepo
from schemas.energy_reading import EnergyReadingCreate
from services.event_queue import EnergyEventQueue
from utils.energy_reading_utils import get_energy_reading

logger = logging.getLogger(__name__)


class EnergyService:
    def __init__(self):
        logger.debug("Initializing EnergyService.")
        self.energy_repo = EnergyRepo()
        self.energy_event_queue = EnergyEventQueue(Config.QUEUE_MAX_COMMIT_SIZE)
        # Lazy import to avoid circular dependency
        self._error_log_service = None

    def _get_error_log_service(self):
        """Lazy load error log service to avoid circular imports."""
        if self._error_log_service is None:
            from services.error_log_service import ErrorLogService

            self._error_log_service = ErrorLogService()
        return self._error_log_service

    async def add_energy_event(self, event: Dict[str, Any]) -> None:
        """Add an energy event to the queue."""
        event["ts"] = datetime.now(timezone(timedelta(hours=-5)))
        await self.energy_event_queue.add_event(event)
        logger.debug("Number of events in energy queue: %d", self.energy_event_queue.queue.qsize())

    def is_queue_full(self) -> bool:
        """Check if the energy event queue is full."""
        return self.energy_event_queue.is_full()

    def is_queue_empty(self) -> bool:
        """Check if the energy event queue is empty."""
        return self.energy_event_queue.is_empty()

    async def process_energy_events(self, get_load_group_id_func, get_device_id_func) -> int:
        """
        Process all energy events in the queue and commit to database.

        Args:
            get_load_group_id_func: Async function to get/create load group ID from friendly name
            get_device_id_func: Async function to get/create device ID from friendly name and description

        Returns:
            Number of events processed
        """
        try:
            if not self.energy_event_queue.is_full():
                return 0

            logger.info("Energy event queue is full. Processing all events.")
            events = []

            while not self.energy_event_queue.is_empty():
                evt = await self.energy_event_queue.get_event()
                payload = evt.get("payload", {})
                friendly_name = evt.get("friendly_name")
                description = evt.get("definition", {}).get("description", "")

                # Get or create load group and device IDs
                load_group_id = await get_load_group_id_func(friendly_name)
                device_id = await get_device_id_func(friendly_name, description)

                # Create energy reading
                energy_reading = get_energy_reading(
                    device_id=device_id,
                    ts=evt.get("ts"),
                    load_group_id=load_group_id,
                    power_watts=payload.get("power"),
                    energy_kwh=payload.get("energy"),
                    voltage_volts=payload.get("voltage"),
                    current_amps=payload.get("current"),
                    power_factor=payload.get("power_factor"),
                    linkquality=payload.get("linkquality"),
                )
                events.append(energy_reading)
                self.energy_event_queue.queue.task_done()

            # Bulk create all energy readings
            async with get_db() as session:
                await self.energy_repo.bulk_create(session, events)
                await session.commit()

            logger.info("Processed and committed %d energy events to database.", len(events))
            return len(events)

        except Exception as e:
            logger.error(f"Error processing energy events: {e}", exc_info=True)
            await self._get_error_log_service().log_exception(
                source="energy_service",
                error_type="processing_error",
                exception=e,
                additional_context="Failed to process energy events from queue",
            )
            return 0

    async def create_energy_reading(
        self,
        load_group_id: Optional[UUID],
        device_id: Optional[UUID],
        ts: Optional[datetime] = None,
        power_watts: Optional[float] = None,
        energy_kwh: Optional[float] = None,
        voltage_volts: Optional[float] = None,
        current_amps: Optional[float] = None,
        power_factor: Optional[float] = None,
        linkquality: Optional[int] = None,
    ) -> EnergyReadingCreate:
        """
        Create an energy reading object.

        Args:
            load_group_id: Load group UUID
            device_id: Device UUID
            ts: Timestamp (defaults to now if not provided)
            power_watts: Power in watts
            energy_kwh: Energy in kilowatt-hours
            voltage_volts: Voltage in volts
            current_amps: Current in amps
            power_factor: Power factor
            linkquality: Link quality

        Returns:
            EnergyReadingCreate schema object
        """
        if ts is None:
            ts = datetime.now(timezone(timedelta(hours=-5)))
        return get_energy_reading(
            device_id=device_id,
            ts=ts,
            load_group_id=load_group_id,
            power_watts=power_watts,
            energy_kwh=energy_kwh,
            voltage_volts=voltage_volts,
            current_amps=current_amps,
            power_factor=power_factor,
            linkquality=linkquality,
        )

    async def bulk_create_energy_readings(self, energy_readings: List[EnergyReadingCreate]) -> None:
        """
        Bulk create energy readings in the database.

        Args:
            energy_readings: List of EnergyReadingCreate objects
        """
        try:
            async with get_db() as session:
                await self.energy_repo.bulk_create(session, energy_readings)
                await session.commit()
            logger.info("Bulk created %d energy readings.", len(energy_readings))
        except Exception as e:
            logger.error(f"Error bulk creating energy readings: {e}", exc_info=True)
            await self._get_error_log_service().log_exception(
                source="energy_service",
                error_type="db_error",
                exception=e,
                additional_context=f"Failed to bulk create {len(energy_readings)} energy readings",
            )
