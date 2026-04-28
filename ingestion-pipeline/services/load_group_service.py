import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from db.models import LoadGroup
from db.session import get_db
from repos.load_group_repo import LoadGroupRepo
from utils.load_group_utils import get_load_group

logger = logging.getLogger(__name__)


class LoadGroupService:
    def __init__(self):
        logger.debug("Initializing LoadGroupService.")
        self.load_group_repo = LoadGroupRepo()
        self.load_groups_cache: Dict[str, LoadGroup] = {}
        # Lazy import to avoid circular dependency
        self._error_log_service = None

    def _get_error_log_service(self):
        """Lazy load error log service to avoid circular imports."""
        if self._error_log_service is None:
            from services.error_log_service import ErrorLogService

            self._error_log_service = ErrorLogService()
        return self._error_log_service

    async def get_all_load_groups(self) -> List[LoadGroup]:
        """Get all load groups from the database and update cache."""
        try:
            async with get_db() as session:
                load_groups = await self.load_group_repo.get_load_groups(session)
                self.load_groups_cache = {lg.name: lg for lg in load_groups}
                return load_groups
        except Exception as e:
            logger.error(f"Error getting all load groups: {e}", exc_info=True)
            await self._get_error_log_service().log_exception(
                source="load_group_service",
                error_type="db_error",
                exception=e,
                additional_context="Failed to get all load groups",
            )
            return []

    async def add_load_group(self, friendly_name: str) -> Optional[UUID]:
        """Add a new load group if it doesn't exist. Returns the load group id (UUID) or None."""
        try:
            if friendly_name in self.load_groups_cache:
                return getattr(self.load_groups_cache[friendly_name], "id", None)
            async with get_db() as session:
                load_group_info = get_load_group(friendly_name)
                if load_group_info:
                    new_lg = await self.load_group_repo.create(session, load_group_info, flush=True)
                    await session.commit()
                    self.load_groups_cache[friendly_name] = new_lg
                    return new_lg.id
        except Exception as e:
            logger.error(f"Error adding load group '{friendly_name}': {e}", exc_info=True)
            await self._get_error_log_service().log_exception(
                source="load_group_service",
                error_type="db_error",
                exception=e,
                additional_context=f"Failed to add load group '{friendly_name}'",
            )
        return None

    def get_load_group_from_cache(self, friendly_name: str) -> Optional[LoadGroup]:
        """Get a load group from the cache by friendly name."""
        return self.load_groups_cache.get(friendly_name)

    def get_load_group_id_from_cache(self, friendly_name: str) -> Optional[UUID]:
        """Get a load group ID from the cache by friendly name."""
        load_group = self.load_groups_cache.get(friendly_name)
        return getattr(load_group, "id", None) if load_group else None

    async def process_load_groups_snapshot(self, devices: List[Dict[str, Any]]) -> bool:
        """
        Process load groups from devices snapshot and sync with database.
        Returns True if any load groups were added.
        """
        try:
            async with get_db() as session:
                logger.info("Processing load groups for devices snapshot")
                load_groups = await self.load_group_repo.get_load_groups(session)
                load_group_names = [lg.name for lg in load_groups]
                self.load_groups_cache = {lg.name: lg for lg in load_groups}
                logger.debug(f"Known load groups: {load_groups}")

                updated = False
                for device in devices:
                    friendly_name = device.get("friendly_name")
                    if friendly_name not in load_group_names:
                        logger.info(f"Friendly name not found in load groups: {friendly_name}")
                        updated = True
                        await self.add_load_group(friendly_name)

                if updated:
                    logger.info("Committing new load groups to database")
                    await session.commit()
                else:
                    logger.debug("No new load groups to add")

                return updated
        except Exception as e:
            logger.error(f"Error processing load groups snapshot: {e}", exc_info=True)
            await self._get_error_log_service().log_exception(
                source="load_group_service",
                error_type="processing_error",
                exception=e,
                additional_context="Failed to process load groups snapshot",
            )
            return False
