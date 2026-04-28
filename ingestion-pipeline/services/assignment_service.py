import asyncio
import logging
from typing import Any, Dict, Optional

from ingest.topic_mapper import EventType, TelemetryEventType
from services.device_rename_service import DeviceRenameService
from services.device_service import DeviceService
from services.energy_service import EnergyService
from services.load_group_service import LoadGroupService
from services.temperature_service import TemperatureService

logger = logging.getLogger(__name__)


class AssignmentService:
    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        logger.debug("Initializing AssignmentService.")
        self.device_service = DeviceService()
        self.load_group_service = LoadGroupService()
        self.energy_service = EnergyService()
        self.temperature_service = TemperatureService()
        self.device_rename_service = DeviceRenameService()
        self.loop = loop or asyncio.get_event_loop()
        self.queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._worker: Optional[asyncio.Task] = None
        # Lazy import to avoid circular dependency
        self._error_log_service = None

    def _get_error_log_service(self):
        """Lazy load error log service to avoid circular imports."""
        if self._error_log_service is None:
            from services.error_log_service import ErrorLogService

            self._error_log_service = ErrorLogService()
        return self._error_log_service

    async def start(self) -> None:
        logger.info("Starting AssignmentService worker loop.")
        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        logger.info("Stopping AssignmentService worker loop.")
        if self._worker is None:
            return
        self._worker.cancel()
        try:
            await self._worker
        except asyncio.CancelledError:
            pass
        self._worker = None

    def submit_event(self, event: Dict[str, Any]) -> None:
        """Thread-safe helper for sync publishers."""
        logger.debug(f"Submitting event: {str(event)[:200]}...")
        asyncio.run_coroutine_threadsafe(self.queue.put(event), self.loop)

    async def _worker_loop(self) -> None:
        logger.debug("Worker loop started.")
        while True:
            event = await self.queue.get()
            try:
                await self._handle_event(event)
            except Exception as e:
                logger.error(f"Error handling event: {e}", exc_info=True)
                await self._get_error_log_service().log_exception(
                    source="assignment_service",
                    error_type="event_handling_error",
                    exception=e,
                    additional_context=f"Failed to handle event of type: {event.get('type', 'unknown')}",
                )
            finally:
                self.queue.task_done()

    async def _handle_event(self, event: Dict[str, Any]) -> None:
        """Dispatch events; extend with real assignment logic."""
        logger.debug(f"Handling event: {str(event)[:200]}...")
        event_type = event.get("type")
        if event_type == EventType.DEVICES_SNAPSHOT.value:
            await self._process_devices(event.get("devices", []))
        elif event_type == EventType.TELEMETRY.value:
            await self._process_telemetry(event)
        elif event_type == EventType.DEVICE_RENAME.value:
            new_device_friendly_name = event.get("data", {}).get("to")
            old_device_friendly_name = event.get("data", {}).get("from")
            to_device_id = await self.device_service.add_and_get_device(new_device_friendly_name)
            from_device_id = await self.device_service.add_and_get_device(old_device_friendly_name)
            event.update({"to_device_id": to_device_id, "from_device_id": from_device_id})
            await self._rename_device(event)
        else:
            logger.debug(f"Ignoring unsupported event type: {event_type}")
            pass

    async def _process_devices(self, devices: list) -> None:
        """Process devices snapshot and update caches."""
        try:
            # Process devices through device service
            await self.device_service.process_devices_snapshot(devices)

            # Process load groups through load group service
            await self.load_group_service.process_load_groups_snapshot(devices)
        except Exception as e:
            logger.error(f"Error processing devices: {e}", exc_info=True)
            await self._get_error_log_service().log_exception(
                source="assignment_service",
                error_type="processing_error",
                exception=e,
                additional_context="Failed to process devices snapshot",
            )

    async def _process_telemetry(self, event: Dict[str, Any]) -> None:
        """Process telemetry event - all operations share one session/transaction."""
        try:
            telemetry_event_type = event.get("telemetry_event_type")
            if telemetry_event_type == TelemetryEventType.ENERGY:
                await self._process_energy_event(event)
            elif telemetry_event_type == TelemetryEventType.TEMPERATURE:
                await self._process_temperature_event(event)
            else:
                logger.warning(f"Unknown telemetry event type: {telemetry_event_type}")
        except Exception as e:
            logger.error(f"Error processing telemetry: {e}", exc_info=True)
            await self._get_error_log_service().log_exception(
                source="assignment_service",
                error_type="processing_error",
                exception=e,
                additional_context=(
                    f"Failed to process telemetry event of type: " f"{event.get('telemetry_event_type', 'unknown')}"
                ),
            )

    async def _process_energy_event(self, event: Dict[str, Any]) -> None:
        """Process a single energy event."""
        try:
            logger.debug(f"Processing energy event: {str(event)[:200]}...")
            await self.energy_service.add_energy_event(event)

            if self.energy_service.is_queue_full():
                await self.energy_service.process_energy_events(
                    get_load_group_id_func=self.load_group_service.add_load_group,
                    get_device_id_func=self.device_service.add_and_get_device,
                )
        except Exception as e:
            logger.error(f"Error processing energy event: {e}", exc_info=True)
            await self._get_error_log_service().log_exception(
                source="assignment_service",
                error_type="processing_error",
                exception=e,
                additional_context=(
                    f"Failed to process energy event for device: " f"{event.get('friendly_name', 'unknown')}"
                ),
            )

    async def _process_temperature_event(self, event: Dict[str, Any]) -> None:
        """Process a single temperature event."""
        try:
            logger.debug(f"Processing temperature event: {str(event)[:200]}...")
            await self.temperature_service.add_temperature_event(event)

            if self.temperature_service.is_queue_full():
                await self.temperature_service.process_temperature_events(
                    get_device_id_func=self.device_service.add_and_get_device
                )
        except Exception as e:
            logger.error(f"Error processing temperature event: {e}", exc_info=True)
            await self._get_error_log_service().log_exception(
                source="assignment_service",
                error_type="processing_error",
                exception=e,
                additional_context=(
                    f"Failed to process temperature event for device: " f"{event.get('friendly_name', 'unknown')}"
                ),
            )

    async def _rename_device(self, event: Dict[str, Any]) -> None:
        """Handle device rename event."""
        try:
            from_device_id = event.get("from_device_id")
            to_device_id = event.get("to_device_id")
            notes = event.get("notes", None)

            if from_device_id and to_device_id:
                await self.device_rename_service.create_rename_record(
                    from_device_id=from_device_id, to_device_id=to_device_id, notes=notes
                )
            else:
                logger.warning("Device rename event missing from_device_id or to_device_id.")
        except Exception as e:
            logger.error(f"Error renaming device: {e}", exc_info=True)
            await self._get_error_log_service().log_exception(
                source="assignment_service",
                error_type="processing_error",
                exception=e,
                additional_context=(
                    f"Failed to rename device from "
                    f"{event.get('data', {}).get('from', 'unknown')} to "
                    f"{event.get('data', {}).get('to', 'unknown')}"
                ),
            )
