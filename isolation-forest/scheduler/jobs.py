from pathlib import Path

from pipeline.sweeps import run_training_sweep_from_file
from utils.logger import get_logger

logger = get_logger(__name__)


async def run_training_sweep_job(config_path: Path) -> None:
    """Run a scheduled training sweep from an external YAML/CSV config."""
    logger.info("Starting scheduled training sweep from %s", config_path)
    run_dir = await run_training_sweep_from_file(config_path=config_path)
    logger.info("Scheduled training sweep completed: %s", run_dir)
