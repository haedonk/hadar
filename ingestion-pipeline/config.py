# config.py
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to sys.path so the shared db/ package is importable
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

load_dotenv()


class Config:
    """Configuration management for the ingestion-pipeline."""

    # MQTT Configuration
    MQTT_HOST: str = os.getenv("MQTT_HOST", "")
    MQTT_PORT: int = int(os.getenv("MQTT_PORT", "1883"))
    MQTT_USER: str | None = os.getenv("MQTT_USER")
    MQTT_PASS: str | None = os.getenv("MQTT_PASS")
    MQTT_BASE_TOPIC: str = os.getenv("MQTT_BASE_TOPIC", "zigbee2mqtt")

    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Application Configuration
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Queue max commit size
    QUEUE_MAX_COMMIT_SIZE: int = int(os.getenv("QUEUE_MAX_COMMIT_SIZE", "20"))


# Create a singleton instance
config = Config()
