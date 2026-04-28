import logging
from typing import Any, Dict, Optional

from db.models.topic_payload_identifier import TopicPayloadIdentifier
from db.session import get_db
from repos.topic_payload_identifier_repo import TopicPayloadIdentifierRepo
from schemas.topic_payload_identifier import TopicPayloadIdentifierCreate, TopicPayloadIdentifierUpdate

logger = logging.getLogger(__name__)


class TopicPayloadIdentifierService:
    def __init__(self):
        logger.debug("Initializing TopicPayloadIdentifierService.")
        self.repo = TopicPayloadIdentifierRepo()
        self.identifiers_cache: Dict[str, TopicPayloadIdentifier] = {}
        # Lazy import to avoid circular dependency
        self._error_log_service = None

    def _get_error_log_service(self):
        """Lazy load error log service to avoid circular imports."""
        if self._error_log_service is None:
            from services.error_log_service import ErrorLogService

            self._error_log_service = ErrorLogService()
        return self._error_log_service

    async def get_all_identifiers(self) -> list[TopicPayloadIdentifier]:
        """Get all topic payload identifiers from the database and update cache."""
        logger.debug("Fetching all topic payload identifiers from database.")
        try:
            async with get_db() as session:
                identifiers_list = await self.repo.get_all(session)
                logger.debug(f"Retrieved {len(identifiers_list)} topic payload identifiers from database.")
                self.identifiers_cache = {identifier.topic: identifier for identifier in identifiers_list}
                logger.debug(f"Updated identifiers cache with {len(self.identifiers_cache)} entries.")
                return identifiers_list
        except Exception as e:
            logger.error(f"Error getting all topic payload identifiers: {e}", exc_info=True)
            await self._get_error_log_service().log_exception(
                source="topic_payload_identifier_service",
                error_type="db_error",
                exception=e,
                additional_context="Failed to get all topic payload identifiers",
            )
            return []

    async def insert_if_not_exists(
        self, topic: str, payload: Dict[str, Any], type: Optional[str] = None
    ) -> Optional[TopicPayloadIdentifier]:
        """Insert a new topic payload identifier if it does not already exist."""
        logger.debug(f"Attempting to insert topic payload identifier for topic '{topic}' if not exists.")
        try:
            existing_identifier = await self.get_by_topic(topic)
            if existing_identifier:
                logger.debug(f"Topic payload identifier for topic '{topic}' already exists.")
                logger.debug(f"Existing identifier ID: {existing_identifier.id}")
                return existing_identifier
            if isinstance(payload, list):
                if len(payload) > 0:
                    logger.debug(
                        f"Payload for topic '{topic}' is a list with {len(payload)} elements, taking the first element."
                    )
                    payload = payload[0]
                else:
                    logger.warning(f"Payload for topic '{topic}' is an empty list, using empty dict instead.")
                    payload = {}

            logger.debug(
                f"Creating new topic payload identifier for topic '{topic}' with payload: {payload}, type: {type}"
            )
            async with get_db() as session:
                identifier_data = TopicPayloadIdentifierCreate(topic=topic, payload=payload, type=type)
                new_identifier = await self.repo.create(session, identifier_data, flush=True)
                await session.commit()
                logger.debug(f"Successfully created topic payload identifier with ID: {new_identifier.id}")
                self.identifiers_cache[new_identifier.topic] = new_identifier
                logger.debug(f"Added new identifier to cache for topic '{new_identifier.topic}'")
                return new_identifier
        except Exception as e:
            logger.error(f"Error inserting topic payload identifier for topic '{topic}': {e}", exc_info=True)
            await self._get_error_log_service().log_exception(
                source="topic_payload_identifier_service",
                error_type="db_error",
                exception=e,
                topic=topic,
                additional_context=f"Failed to insert topic payload identifier for topic '{topic}'",
            )
            return None

    async def get_by_topic(self, topic: str) -> Optional[TopicPayloadIdentifier]:
        """Get topic payload identifier for a specific topic (returns first match)."""
        logger.debug(f"Looking up topic payload identifier for topic '{topic}'")
        try:
            if topic in self.identifiers_cache:
                logger.debug(f"Found topic '{topic}' in cache (ID: {self.identifiers_cache[topic].id})")
                return self.identifiers_cache[topic]

            logger.debug(f"Topic '{topic}' not in cache, querying database.")
            async with get_db() as session:
                identifiers = await self.repo.get_by_topic(session, topic)
                if identifiers:
                    logger.debug(
                        f"Found {len(identifiers)} identifier(s) for topic "
                        f"'{topic}', caching first match (ID: {identifiers[0].id})"
                    )
                    # Cache the first match
                    self.identifiers_cache[topic] = identifiers[0]
                    return identifiers[0]
                logger.debug(f"No identifier found for topic '{topic}'")
                return None
        except Exception as e:
            logger.error(f"Error getting topic payload identifier for topic '{topic}': {e}", exc_info=True)
            await self._get_error_log_service().log_exception(
                source="topic_payload_identifier_service",
                error_type="db_error",
                exception=e,
                topic=topic,
                additional_context=f"Failed to get topic payload identifier for topic '{topic}'",
            )
            return None

    async def create_identifier(
        self, topic: str, payload: Dict[str, Any], type: Optional[str] = None
    ) -> Optional[TopicPayloadIdentifier]:
        """Create a new topic payload identifier."""
        logger.debug(f"Creating new topic payload identifier for topic '{topic}' with payload: {payload}, type: {type}")
        try:
            async with get_db() as session:
                identifier_data = TopicPayloadIdentifierCreate(topic=topic, payload=payload, type=type)
                new_identifier = await self.repo.create(session, identifier_data, flush=True)
                await session.commit()
                logger.debug(f"Successfully created topic payload identifier with ID: {new_identifier.id}")
                self.identifiers_cache[new_identifier.topic] = new_identifier
                logger.debug(f"Added identifier to cache for topic '{new_identifier.topic}'")
                return new_identifier
        except Exception as e:
            logger.error(f"Error creating topic payload identifier: {e}", exc_info=True)
            await self._get_error_log_service().log_exception(
                source="topic_payload_identifier_service",
                error_type="db_error",
                exception=e,
                topic=topic,
                additional_context=f"Failed to create topic payload identifier for topic '{topic}'",
            )
            return None

    async def update_identifier(
        self,
        identifier_id: int,
        topic: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        type: Optional[str] = None,
    ) -> Optional[TopicPayloadIdentifier]:
        """Update an existing topic payload identifier."""
        logger.debug(
            f"Updating topic payload identifier {identifier_id} with topic={topic}, payload={payload}, type={type}"
        )
        try:
            async with get_db() as session:
                identifier = await self.repo.get_by_id(session, identifier_id)
                if not identifier:
                    logger.warning(f"Topic payload identifier {identifier_id} not found")
                    return None

                old_topic = identifier.topic
                logger.debug(f"Current topic for identifier {identifier_id}: '{old_topic}'")
                update_data = TopicPayloadIdentifierUpdate(topic=topic, payload=payload, type=type)
                updated_identifier = await self.repo.update(session, identifier, update_data, flush=True)
                await session.commit()
                logger.debug(f"Successfully updated topic payload identifier {identifier_id}")

                if updated_identifier:
                    # Remove old cache entry if topic changed
                    if topic and topic != old_topic and old_topic in self.identifiers_cache:
                        logger.debug(f"Topic changed from '{old_topic}' to '{topic}', removing old cache entry")
                        del self.identifiers_cache[old_topic]
                    self.identifiers_cache[updated_identifier.topic] = updated_identifier
                    logger.debug(f"Updated cache with new topic '{updated_identifier.topic}'")
                return updated_identifier
        except Exception as e:
            logger.error(f"Error updating topic payload identifier {identifier_id}: {e}", exc_info=True)
            await self._get_error_log_service().log_exception(
                source="topic_payload_identifier_service",
                error_type="db_error",
                exception=e,
                topic=topic,
                additional_context=f"Failed to update topic payload identifier {identifier_id}",
            )
            return None

    def get_from_cache(self, topic: str) -> Optional[TopicPayloadIdentifier]:
        """Get a topic payload identifier from the cache by topic name."""
        logger.debug(f"Getting topic payload identifier from cache for topic '{topic}'")
        result = self.identifiers_cache.get(topic)
        if result:
            logger.debug(f"Found topic '{topic}' in cache (ID: {result.id})")
        else:
            logger.debug(f"Topic '{topic}' not found in cache")
        return result
