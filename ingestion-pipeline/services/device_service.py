import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from db.models import Device
from db.session import get_db
from repos.device_repo import DeviceRepo
from utils.device_utils import get_device
from utils.device_utils import update_device_description as get_device_update

logger = logging.getLogger(__name__)


def _get_device_type(description: str) -> str:
    """Determine device type based on description."""
    description_lower = description.lower()
    if "plug" in description_lower:
        return "plug"
    elif "bulb" in description_lower:
        return "bulb"
    elif "temperature" in description_lower:
        return "temperature"
    else:
        return "Unknown"


class DeviceService:
    def __init__(self):
        logger.debug("Initializing DeviceService.")
        self.device_repo = DeviceRepo()
        self.devices_cache: Dict[str, Device] = {}
        # Lazy import to avoid circular dependency
        self._error_log_service = None

    def _get_error_log_service(self):
        """Lazy load error log service to avoid circular imports."""
        if self._error_log_service is None:
            from services.error_log_service import ErrorLogService

            self._error_log_service = ErrorLogService()
        return self._error_log_service

    async def get_all_devices(self) -> List[Device]:
        """Get all devices from the database and update cache."""
        try:
            async with get_db() as session:
                devices_list = await self.device_repo.get_devices(session)
                self.devices_cache = {device.device_label: device for device in devices_list}
                return devices_list
        except Exception as e:
            logger.error(f"Error getting all devices: {e}", exc_info=True)
            return []

    async def add_and_get_device(self, friendly_name: str, description: str = None) -> Optional[UUID]:
        """Add a new device if it doesn't exist. Returns the device id (UUID) or None."""
        try:
            if friendly_name in self.devices_cache:
                return getattr(self.devices_cache[friendly_name], "id", None)
            async with get_db() as session:
                device_type = _get_device_type(description) if description else "Unknown"
                device_info = get_device(friendly_name, device_type, description)
                if device_info:
                    new_device = await self.device_repo.create(session, device_info, flush=True)
                    await session.commit()
                    self.devices_cache[friendly_name] = new_device
                    return new_device.id
        except Exception as e:
            logger.error(f"Error adding device '{friendly_name}': {e}", exc_info=True)
        return None

    async def update_device_description_type(self, friendly_name: str, description: str) -> None:
        """Update the description of an existing device."""
        try:
            if friendly_name not in self.devices_cache:
                logger.warning(f"Device '{friendly_name}' not found in cache")
                return

            device = self.devices_cache[friendly_name]
            device_type = _get_device_type(description)
            device_update = get_device_update(device.id, description, device_type)
            async with get_db() as session:
                updated_device = await self.device_repo.update(session, device, device_update, flush=True)
                await session.commit()
                # Update cache with new description
                if updated_device:
                    self.devices_cache[friendly_name] = updated_device
        except Exception as e:
            logger.error(f"Error updating device '{friendly_name}': {e}", exc_info=True)

    def get_device_from_cache(self, friendly_name: str) -> Optional[Device]:
        """Get a device from the cache by friendly name."""
        return self.devices_cache.get(friendly_name)

    def get_device_id_from_cache(self, friendly_name: str) -> Optional[UUID]:
        """Get a device ID from the cache by friendly name."""
        device = self.devices_cache.get(friendly_name)
        return getattr(device, "id", None) if device else None

    async def process_devices_snapshot(self, devices: List[Dict[str, Any]]) -> bool:
        """
        Process devices snapshot and sync with database.
        Returns True if any devices were added or updated.
        """
        try:
            async with get_db() as session:
                logger.info("Processing devices snapshot")
                devices_list = await self.device_repo.get_devices(session)
                device_labels = [device.device_label for device in devices_list]
                self.devices_cache = {device.device_label: device for device in devices_list}
                logger.debug(f"Known devices: {devices_list}")

                updated = False
                sample = devices[10] if len(devices) > 10 else devices[0] if devices else "No devices"
                logger.debug(f"Single device payload example: {sample}")

                for device in devices:
                    friendly_name = device.get("friendly_name")
                    description = device.get("definition", {}).get("description", "")
                    device_type = _get_device_type(description)
                    logger.debug(f"Processing device: {friendly_name}, Description: {description}, Type: {device_type}")

                    if friendly_name not in device_labels:
                        logger.info(f"Friendly name not found in devices: {friendly_name}")
                        updated = True
                        await self.add_and_get_device(friendly_name, description)
                    else:
                        for dev in devices_list:
                            if dev.device_label == friendly_name and dev.description != description:
                                logger.info(f"Updating description for device: {friendly_name}")
                                await self.update_device_description_type(friendly_name, description)
                                updated = True

                if updated:
                    logger.info("Committing device changes to database")
                    await session.commit()
                else:
                    logger.debug("No device changes to commit")

                return updated
        except Exception as e:
            logger.error(f"Error processing devices snapshot: {e}", exc_info=True)
            await self._get_error_log_service().log_exception(
                source="device_service",
                error_type="processing_error",
                exception=e,
                additional_context="Failed to process devices snapshot",
            )
            return False
