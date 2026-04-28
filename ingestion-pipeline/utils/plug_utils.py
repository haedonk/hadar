import logging

from schemas.plug import PlugCreate

logger = logging.getLogger(__name__)


def get_plug(name: str) -> PlugCreate:
    """Create a PlugCreate schema from a name."""
    logger.debug(f"Creating PlugCreate for name={name}")
    return PlugCreate(plug_label=name)
