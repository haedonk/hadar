import logging
from typing import Optional
from uuid import UUID

from db.session import get_db
from repos.device_rename_repo import DeviceRenameRepo
from schemas.device_rename import DeviceRenameCreate

logger = logging.getLogger(__name__)


class DeviceRenameService:
    """
    Service for managing device rename records.
    Tracks the history of device name changes.
    """

    def __init__(self):
        logger.debug("Initializing DeviceRenameService.")
        self.device_rename_repo = DeviceRenameRepo()
        # Lazy import to avoid circular dependency
        self._error_log_service = None

    def _get_error_log_service(self):
        """Lazy load error log service to avoid circular imports."""
        if self._error_log_service is None:
            from services.error_log_service import ErrorLogService

            self._error_log_service = ErrorLogService()
        return self._error_log_service

    async def create_rename_record(self, from_device_id: UUID, to_device_id: UUID, notes: Optional[str] = None) -> bool:
        """
        Create a device rename record to track when a device is renamed.

        Args:
            from_device_id: The UUID of the original device
            to_device_id: The UUID of the new device
            notes: Optional notes about the rename

        Returns:
            True if the record was created successfully, False otherwise
        """
        try:
            if from_device_id == to_device_id:
                logger.warning(f"Attempted to create rename record with same device ID: {from_device_id}")
                return False

            logger.info(f"Creating device rename record from {from_device_id} to {to_device_id}")

            rename_data = DeviceRenameCreate(from_id=from_device_id, to_id=to_device_id, notes=notes)

            async with get_db() as session:
                await self.device_rename_repo.create(session, rename_data, flush=True)
                await session.commit()

            logger.info(f"Successfully created device rename record from {from_device_id} to {to_device_id}")
            return True

        except Exception as e:
            logger.error(f"Error creating device rename record: {e}", exc_info=True)
            await self._get_error_log_service().log_exception(
                source="device_rename_service",
                error_type="db_error",
                exception=e,
                additional_context=f"Failed to create device rename record from {from_device_id} to {to_device_id}",
            )
            return False

    async def track_device_name_change(
        self,
        old_device_label: str,
        new_device_label: str,
        old_device_id: UUID,
        new_device_id: UUID,
        notes: Optional[str] = None,
    ) -> bool:
        """
        Track a device name change by creating a rename record.
        This is a convenience method that provides more context in logs.

        Args:
            old_device_label: The old device friendly name
            new_device_label: The new device friendly name
            old_device_id: The UUID of the original device
            new_device_id: The UUID of the new device
            notes: Optional notes (auto-generated if not provided)

        Returns:
            True if the record was created successfully, False otherwise
        """
        # Auto-generate notes if not provided
        if notes is None:
            notes = f"Device renamed from '{old_device_label}' to '{new_device_label}'"

        logger.debug(f"Tracking device name change: {old_device_label} -> {new_device_label}")

        return await self.create_rename_record(from_device_id=old_device_id, to_device_id=new_device_id, notes=notes)
