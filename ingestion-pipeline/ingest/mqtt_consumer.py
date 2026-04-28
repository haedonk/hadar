# ingest/mqtt_consumer.py
import asyncio
import json
import logging
import threading

import paho.mqtt.client as mqtt

from config import config
from ingest.topic_mapper import TopicMapper
from services.assignment_service import AssignmentService
from services.topic_payload_identifier_service import TopicPayloadIdentifierService

logger = logging.getLogger(__name__)


class MQTTConsumer:
    def __init__(self, host=None, port=None, user=None, password=None, base_topic=None):
        self.host = host or config.MQTT_HOST
        self.port = port or config.MQTT_PORT
        self.user = user or config.MQTT_USER
        self.password = password or config.MQTT_PASS
        self.base_topic = base_topic or config.MQTT_BASE_TOPIC
        self.client = None
        self.topic_service = TopicPayloadIdentifierService()
        self.assignment_loop = asyncio.new_event_loop()
        self.assignment_service = AssignmentService(loop=self.assignment_loop)
        self.topic_mapper = TopicMapper(base_topic=self.base_topic)
        self._assignment_thread: threading.Thread | None = None
        # Lazy import to avoid circular dependency
        self._error_log_service = None

    def _get_error_log_service(self):
        """Lazy load error log service to avoid circular imports."""
        if self._error_log_service is None:
            from services.error_log_service import ErrorLogService

            self._error_log_service = ErrorLogService()
        return self._error_log_service

    def _ensure_assignment_worker(self) -> None:
        if self._assignment_thread and self._assignment_thread.is_alive():
            return
        self._assignment_thread = threading.Thread(
            target=self.assignment_loop.run_forever,
            name="assignment-loop",
            daemon=True,
        )
        self._assignment_thread.start()
        asyncio.run_coroutine_threadsafe(self.assignment_service.start(), self.assignment_loop)
        asyncio.run_coroutine_threadsafe(self.topic_service.get_all_identifiers(), self.assignment_loop)
        logger.debug("Assignment worker ensured and started if not alive.")

    def on_connect(self, client, userdata, flags, rc, properties=None):
        logger.info(f"Connected: {rc}")

        # Retained list of all devices (includes ieee_address + friendly_name)
        client.subscribe(f"{self.base_topic}/bridge/devices")

        # Device telemetry
        client.subscribe(f"{self.base_topic}/#")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8", errors="ignore")
            logger.debug(f"Received message on topic {topic}: {payload[:200]}...")

            # Use TopicMapper to parse the topic and create an event
            event = self.topic_mapper.parse_topic(topic, payload)

            # Check if the event should be processed
            if event and self.topic_mapper.should_process_event(event):
                logger.debug(f"Submitting event of type '{event.get('type')}' to assignment service")
                self.assignment_service.submit_event(event)
            elif event:
                logger.debug(f"Ignoring event of type '{event.get('type')}'")
            else:
                logger.debug(f"No event created for topic {topic}")

            # Parse payload for topic service, handle empty payload case
            try:
                parsed_payload = json.loads(payload) if payload and payload.strip() else {}
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON payload for topic {topic}, using empty dict")
                parsed_payload = {}

            asyncio.run_coroutine_threadsafe(
                self.topic_service.insert_if_not_exists(
                    topic, parsed_payload, event.get("type", None) if event else None
                ),
                self.assignment_loop,
            )
        except Exception as e:
            logger.error(f"Error processing message from topic {msg.topic}: {e}", exc_info=True)
            # Log to error database asynchronously
            asyncio.run_coroutine_threadsafe(
                self._get_error_log_service().log_exception(
                    source="mqtt_consumer",
                    error_type="message_processing_error",
                    exception=e,
                    topic=msg.topic,
                    additional_context=f"Failed to process message from topic {msg.topic}",
                ),
                self.assignment_loop,
            )

    def start(self):
        """Start the MQTT consumer and listen for messages."""
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        if self.user and self.password:
            self.client.username_pw_set(self.user, self.password)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self._ensure_assignment_worker()
        self.client.connect(self.host, self.port, keepalive=60)
        logger.info("MQTT consumer started and connected to broker.")
        self.client.loop_forever()


if __name__ == "__main__":
    consumer = MQTTConsumer()
    consumer.start()
