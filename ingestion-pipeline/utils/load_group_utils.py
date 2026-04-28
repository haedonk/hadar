import logging

from schemas.load_group import LoadGroupCreate

logger = logging.getLogger(__name__)


def get_load_group(name: str) -> LoadGroupCreate:
    """Create a LoadGroupCreate schema from a name."""
    logger.debug(f"Creating LoadGroupCreate for name={name}")
    return LoadGroupCreate(name=name)
