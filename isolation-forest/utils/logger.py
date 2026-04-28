import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

from config import config


def setup_logging() -> tuple[Path, Path]:
    """Configure logging with console and file handlers.

    Creates timestamped directories for the current run in logs/ and output/.
    Returns the paths to the run-specific log and output directories.
    """
    # Create timestamped directories
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Base directories
    data_base_dir = Path(config.DATA_DIR)
    logs_base_dir = data_base_dir / "logs"
    output_base_dir = data_base_dir / "output"

    # Run-specific directories
    logs_base_dir.mkdir(parents=True, exist_ok=True)
    output_base_dir.mkdir(parents=True, exist_ok=True)

    run_logs_dir = logs_base_dir / timestamp
    run_output_dir = output_base_dir / timestamp

    run_logs_dir.mkdir(exist_ok=True)
    run_output_dir.mkdir(exist_ok=True)

    # Configure project logger (not root) to avoid third-party noise
    logger = logging.getLogger("isolation_forest")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Remove existing handlers
    logger.handlers.clear()

    # Get log level from config
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)

    # Console handler - uses config level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler - always DEBUG level with rotation
    log_file = run_logs_dir / "run.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    logger.info(f"Logging initialized. Logs directory: {run_logs_dir}")
    logger.info(f"Output directory: {run_output_dir}")

    return run_logs_dir, run_output_dir


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the project namespace."""
    return logging.getLogger(f"isolation_forest.{name}")
