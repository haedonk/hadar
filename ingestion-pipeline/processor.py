import logging

from config import config

# Configure logging globally based on LOG_LEVEL
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from ingest.mqtt_consumer import MQTTConsumer  # noqa: E402 — logging must be configured first

if __name__ == "__main__":
    consumer = MQTTConsumer()
    consumer.start()
