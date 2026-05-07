import asyncio
import logging

from config import config
from scheduler.service import run_scoring_service


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


async def main() -> None:
    """Entry point for the scoring pipeline service."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Scoring pipeline service starting")
    logger.info("Hourly output directory: %s", config.HOURLY_SCORING_OUTPUT_DIR)
    logger.info("Lookback hours: %s", config.HOURLY_SCORING_LOOKBACK_HOURS)
    await run_scoring_service()


if __name__ == "__main__":
    asyncio.run(main())
