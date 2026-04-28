import logging
from uuid import UUID

from schemas.device import DeviceCreate, DeviceUpdate

logger = logging.getLogger(__name__)


def get_device(label: str, device_type: str = "plug", description: str = "") -> DeviceCreate:
    """Create a DeviceCreate schema from a label, device type, and description."""
    logger.debug(f"Creating DeviceCreate for label={label}, type={device_type}, description={description}")
    return DeviceCreate(device_label=label, device_type=device_type, description=description)


def update_device_description(device_id: UUID, device_description: str, device_type: str) -> DeviceUpdate:
    """Create a DeviceUpdate schema to update the device description."""
    logger.debug(f"Updating Device id={device_id} with new description={device_description}")
    return DeviceUpdate(description=device_description, device_type=device_type)
