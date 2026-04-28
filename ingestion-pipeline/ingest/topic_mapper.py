import json
import logging
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Enumeration of event types that can be generated from MQTT topics."""

    DEVICES_SNAPSHOT = "devices_snapshot"
    DEVICE_RENAME = "device_rename"
    TELEMETRY = "telemetry"
    BRIDGE_STATE = "bridge_state"
    BRIDGE_LOG = "bridge_log"
    BRIDGE_INFO = "bridge_info"
    UNKNOWN = "unknown"


class TelemetryEventType(Enum):
    """Enumeration of telemetry event subtypes."""

    TEMPERATURE = "temperature"
    ENERGY = "energy"
    OTHER = "other"


class TopicMapper:
    """
    Maps MQTT topics to structured events for processing.
    Handles topic parsing and event creation based on topic patterns.
    """

    # Configuration: Event types that should be processed by the assignment service
    PROCESSABLE_EVENT_TYPES = {
        EventType.DEVICES_SNAPSHOT,
        EventType.TELEMETRY,
        EventType.DEVICE_RENAME,
        # EventType.BRIDGE_STATE,     # Uncomment to enable
    }

    def __init__(self, base_topic: str = "zigbee2mqtt"):
        """
        Initialize the TopicMapper.

        Args:
            base_topic: The base MQTT topic (e.g., "zigbee2mqtt")
        """
        self.base_topic = base_topic
        self.bridge_devices_topic = f"{base_topic}/bridge/devices"
        self.bridge_state_topic = f"{base_topic}/bridge/state"
        self.bridge_log_topic = f"{base_topic}/bridge/log"
        self.bridge_info_topic = f"{base_topic}/bridge/info"
        self.bridge_prefix = f"{base_topic}/bridge/"
        self.bridge_devices_rename_topic = f"{base_topic}/bridge/response/device/rename"
        # Lazy import to avoid circular dependency
        self._error_log_service = None

        logger.debug(f"TopicMapper initialized with base_topic: {base_topic}")

    def _get_error_log_service(self):
        """Lazy load error log service to avoid circular imports."""
        if self._error_log_service is None:
            from services.error_log_service import ErrorLogService

            self._error_log_service = ErrorLogService()
        return self._error_log_service

    def parse_topic(self, topic: str, payload: str) -> Optional[Dict[str, Any]]:
        """
        Parse an MQTT topic and payload into a structured event.

        Args:
            topic: The MQTT topic
            payload: The message payload as a string

        Returns:
            A dictionary representing the event, or None if the topic should be ignored
        """
        try:
            # Parse JSON payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from topic {topic}: {payload[:100]}")
                return None

            # Route based on topic
            if topic == self.bridge_devices_topic:
                if not isinstance(data, list):
                    logger.warning(f"Expected list for devices snapshot, got {type(data)}")
                    data = []
                logger.info(f"Creating devices snapshot event with {len(data)} devices")
                return self._create_event(EventType.DEVICES_SNAPSHOT, devices=data)

            elif topic == self.bridge_state_topic:
                logger.debug(f"Creating bridge state event: {data.get('state', 'unknown')}")
                return self._create_event(EventType.BRIDGE_STATE, state=data.get("state", "unknown"), data=data)

            elif topic == self.bridge_log_topic:
                logger.debug(f"Creating bridge log event: {data.get('type', 'unknown')}")
                return self._create_event(
                    EventType.BRIDGE_LOG,
                    log_type=data.get("type", "unknown"),
                    message=data.get("message", ""),
                    data=data,
                )

            elif topic == self.bridge_info_topic:
                logger.debug("Creating bridge info event")
                return self._create_event(EventType.BRIDGE_INFO, version=data.get("version", "unknown"), data=data)

            elif topic == self.bridge_devices_rename_topic:
                logger.debug("Creating devices rename event")
                return self._create_event(EventType.DEVICE_RENAME, data=data.get("data", {}))

            elif topic.startswith(self.bridge_prefix):
                # Ignore other bridge topics
                logger.debug(f"Ignoring bridge topic: {topic}")
                return None

            elif topic.startswith(self.base_topic):
                # Device telemetry topic: zigbee2mqtt/<friendly_name>
                friendly_name = self._extract_friendly_name(topic)
                logger.debug(f"Creating telemetry event for device: {friendly_name}")
                return self._create_event(
                    EventType.TELEMETRY,
                    telemetry_event_type=self._get_telemetry_event_type(data),
                    friendly_name=friendly_name,
                    payload=data,
                    definition=data.get("definition", {}),
                )

            else:
                logger.warning(f"Unknown topic pattern: {topic}")
                return self._create_event(EventType.UNKNOWN, topic=topic, data=data)

        except Exception as e:
            logger.error(f"Error parsing topic {topic}: {e}", exc_info=True)
            # Note: parse_topic is synchronous, so we can't use async error logging here
            # The error will be logged through the console logger
            # Consider refactoring to async if database logging is critical
            return None

    def _get_telemetry_event_type(self, payload: Dict[str, Any]) -> TelemetryEventType:
        """
        Determine the telemetry event subtype based on payload content.

        Args:
            payload: The telemetry payload dictionary

        Returns:
            The TelemetryEventType enum value
        """
        if "temperature" in payload:
            return TelemetryEventType.TEMPERATURE
        elif "energy" in payload or "power" in payload:
            return TelemetryEventType.ENERGY
        else:
            return TelemetryEventType.OTHER

    def _create_event(self, event_type: EventType, **kwargs) -> Dict[str, Any]:
        """
        Create a generic event with the given type and additional fields.

        Args:
            event_type: The EventType enum value
            **kwargs: Additional fields to include in the event

        Returns:
            A dictionary representing the event
        """
        event = {"type": event_type.value}
        event.update(kwargs)
        return event

    def _extract_friendly_name(self, topic: str) -> str:
        """
        Extract the friendly name from a device telemetry topic.

        Args:
            topic: The MQTT topic (e.g., "zigbee2mqtt/living_room_sensor")

        Returns:
            The friendly name of the device
        """
        # Remove base topic and leading slash
        friendly_name = topic[len(self.base_topic) + 1 :]
        return friendly_name

    def should_process_event(self, event: Optional[Dict[str, Any]]) -> bool:
        """
        Determine if an event should be processed.

        Args:
            event: The event dictionary

        Returns:
            True if the event should be processed, False otherwise
        """
        if event is None:
            return False

        event_type = event.get("type")

        # Check if event type is in the configured processable types
        try:
            event_enum = EventType(event_type)
            return event_enum in self.PROCESSABLE_EVENT_TYPES
        except ValueError:
            # Unknown event type
            return False

    def get_event_type(self, event: Dict[str, Any]) -> EventType:
        """
        Get the EventType enum from an event dictionary.

        Args:
            event: The event dictionary

        Returns:
            The EventType enum value
        """
        event_type_str = event.get("type", "unknown")
        try:
            return EventType(event_type_str)
        except ValueError:
            return EventType.UNKNOWN
