from pathlib import Path

import pandas as pd

from utils.logger import get_logger

logger = get_logger(__name__)


def test_deduplication(df: pd.DataFrame, output_dir: Path | None = None) -> None:
    """Verify that no duplicate (device, timestamp, temperature) rows remain."""
    logger.info("Testing deduplication...")
    dupes = df[
        df.duplicated(
            subset=["device_label", "datetime", "temperature"],
            keep=False,
        )
    ]

    logger.info("Found %d duplicate rows", len(dupes))

    if output_dir:
        dupes_file = output_dir / "duplicates.csv"
        dupes.to_csv(dupes_file, index=False)
        logger.info("Duplicate rows saved to %s", dupes_file)

        # Save duplicate summary
        dupes_summary = (
            dupes.groupby(["device_label", "datetime", "temperature"])
            .size()
            .sort_values(ascending=False)
            .head(20)
            .reset_index(name="count")
        )
        summary_file = output_dir / "duplicates_summary.csv"
        dupes_summary.to_csv(summary_file, index=False)
        logger.info("Duplicate summary saved to %s", summary_file)
    else:
        logger.debug("Duplicate sample:\n%s", dupes.head(20))
        logger.debug(
            "Duplicate counts:\n%s",
            dupes.groupby(["device_label", "datetime", "temperature"]).size().sort_values(ascending=False).head(20),
        )
