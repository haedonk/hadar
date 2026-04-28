import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

# Add project root to sys.path so the shared db/ package is importable
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

load_dotenv()


class Config:
    """Configuration management for the isolation-forest pipeline."""

    DEFAULT_DATA_DIR: str = str(Path(__file__).resolve().parent)
    DATA_DIR: str = os.getenv("HADAR_DATA_DIR", DEFAULT_DATA_DIR)

    DB_DRIVER: str = os.getenv("DB_DRIVER", "postgresql+asyncpg")
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "")

    DATABASE_URL: str = f"{DB_DRIVER}://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    SAVE_CSV: bool = os.getenv("SAVE_CSV", "False").lower() in ("true", "1", "yes")

    CLEAN_DATA: bool = os.getenv("CLEAN_DATA", "True").lower() in ("true", "1", "yes")


config = Config()
