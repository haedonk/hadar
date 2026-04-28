import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.topic_payload_identifier import TopicPayloadIdentifier
from schemas.topic_payload_identifier import TopicPayloadIdentifierCreate, TopicPayloadIdentifierUpdate

logger = logging.getLogger(__name__)


class TopicPayloadIdentifierRepo:
    """Data access layer for TopicPayloadIdentifier records."""

    async def create(
        self, session: AsyncSession, data: TopicPayloadIdentifierCreate, *, flush: bool = False
    ) -> TopicPayloadIdentifier:
        logger.debug(f"Creating topic payload identifier with data: {data}")
        identifier = TopicPayloadIdentifier(**data.model_dump(exclude_unset=True))
        session.add(identifier)
        if flush:
            await session.flush()
        return identifier

    async def update(
        self,
        session: AsyncSession,
        identifier: TopicPayloadIdentifier,
        data: TopicPayloadIdentifierUpdate,
        *,
        flush: bool = False,
    ) -> TopicPayloadIdentifier:
        logger.debug(f"Updating topic payload identifier {identifier} with data: {data}")
        identifier = await session.merge(identifier)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(identifier, field, value)
        if flush:
            await session.flush()
        return identifier

    async def get_all(self, session: AsyncSession) -> list[TopicPayloadIdentifier]:
        logger.debug("Fetching all topic payload identifiers.")
        result = await session.execute(select(TopicPayloadIdentifier))
        return list(result.scalars().all())

    async def get_by_id(self, session: AsyncSession, identifier_id: int) -> TopicPayloadIdentifier | None:
        logger.debug(f"Fetching topic payload identifier by id: {identifier_id}")
        result = await session.execute(
            select(TopicPayloadIdentifier).where(TopicPayloadIdentifier.id == identifier_id)  # type: ignore
        )
        return result.scalars().first()

    async def get_by_topic(self, session: AsyncSession, topic: str) -> list[TopicPayloadIdentifier]:
        logger.debug(f"Fetching topic payload identifiers by topic: {topic}")
        result = await session.execute(
            select(TopicPayloadIdentifier).where(TopicPayloadIdentifier.topic == topic)  # type: ignore
        )
        return list(result.scalars().all())
