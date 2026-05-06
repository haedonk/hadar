import asyncio

from config import config
from pipeline.cleaning import clean_data
from pipeline.data_access import fetch_temperature_readings_df
from pipeline.detection import run_per_device_isolation
from pipeline.visualization import plot_anomaly_bar_chart, plot_anomaly_scatter
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


async def main() -> None:
    """Fetch data, run per-device temperature anomaly detection, and generate visualizations."""
    # Setup logging and get run directories
    logs_dir, output_dir = setup_logging()
    logger.info("Starting temperature anomaly detection pipeline")

    df = await fetch_temperature_readings_df()
    logger.info(f"Fetched {len(df)} rows")
    logger.debug(f"DataFrame head:\n{df.head()}")

    if config.CLEAN_DATA:
        logger.info("Cleaning data...")
        df = clean_data(df, output_dir)
        logger.info(f"After cleaning: {len(df)} rows")
        logger.debug(f"Cleaned DataFrame head:\n{df.head()}")

    # Run a separate Isolation Forest per device
    logger.info("Running per-device Isolation Forest...")
    df, summary_df = run_per_device_isolation(df)

    # Summary
    anomalies = df[df["anomaly"] == -1]
    logger.info(f"Total anomalies detected: {len(anomalies)} / {len(df)} " f"({len(anomalies) / len(df) * 100:.1f}%)")
    logger.debug(f"Anomalies:\n{anomalies}")

    # Save device summary to output directory
    summary_file = output_dir / "device_summary.csv"
    summary_df.to_csv(summary_file, index=False)
    logger.info(f"Device summary saved to {summary_file}")

    # Save full results to output directory
    if config.SAVE_CSV:
        results_file = output_dir / "results.csv"
        df.to_csv(results_file, index=False)
        logger.info(f"Results saved to {results_file}")
    else:
        logger.debug("CSV saving disabled (SAVE_CSV=False)")

    # Visualizations
    plot_anomaly_bar_chart(df, output_dir)
    plot_anomaly_scatter(df, output_dir)

    logger.info("Pipeline completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
