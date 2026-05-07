import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

# Add project root to sys.path so shared db/ is importable.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

load_dotenv()


class Config:
    """Configuration for the HADAR scoring pipeline service."""

    DEFAULT_DATA_DIR: str = "/mnt/hadar-data"
    DATA_DIR: str = os.getenv("HADAR_DATA_DIR", DEFAULT_DATA_DIR)
    HOURLY_SCORING_OUTPUT_DIR: str = os.getenv(
        "HOURLY_SCORING_OUTPUT_DIR",
        str(Path(DATA_DIR) / "output" / "hourly-scoring-runs"),
    )
    HOURLY_SCORING_LOOKBACK_HOURS: float = float(os.getenv("HOURLY_SCORING_LOOKBACK_HOURS", "1"))
    HOURLY_SCORING_OFFSET_HOURS: float = float(os.getenv("HOURLY_SCORING_OFFSET_HOURS", "1"))
    FEATURE_CONTEXT_HOURS: float = float(os.getenv("FEATURE_CONTEXT_HOURS", "6"))
    MODEL_ARTIFACT_DIR: str = os.getenv(
        "MODEL_ARTIFACT_DIR",
        "/mnt/hadar-model-data/output/training-sweeps/20260506T220024Z_comprehensive-training-sweep/"
        "configs/full_c003_e100/models",
    )
    MODEL_RUN_ID: str = os.getenv("MODEL_RUN_ID", "20260506T220024Z_comprehensive-training-sweep")
    MODEL_CONFIG_NAME: str = os.getenv("MODEL_CONFIG_NAME", "full_c003_e100")
    SCHEDULER_TIMEZONE: str = os.getenv("SCHEDULER_TIMEZONE", "America/New_York")
    OUTPUT_TIMEZONE: str = os.getenv("OUTPUT_TIMEZONE", SCHEDULER_TIMEZONE)
    SCHEDULER_CONFIG_PATH: str = os.getenv(
        "SCHEDULER_CONFIG_PATH",
        str(Path(__file__).resolve().parent / "configs" / "scheduler" / "scheduler.yaml"),
    )

    DB_DRIVER: str = os.getenv("DB_DRIVER", "postgresql+asyncpg")
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "")

    DATABASE_URL: str = f"{DB_DRIVER}://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


config = Config()
