"""Scheduler service for hourly scoring exports."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta
from pathlib import Path
from typing import Any

from config import config
from pipeline.export import export_recent_readings_csv
from pipeline.promotion import load_promoted_model
from scheduler.config import ScheduledScoringJobConfig, ScoringSchedulerConfig, load_scheduler_config

logger = logging.getLogger(__name__)

Exporter = Callable[[], Awaitable[Any]]
SchedulerFactory = Callable[[str], Any]
WaitForever = Callable[[], Awaitable[None]]

HOURLY_EXPORT_JOB_ID = "hourly_recent_readings_csv_export"


async def run_scoring_service(
    *,
    exporter: Exporter | None = None,
    scheduler_config: ScoringSchedulerConfig | None = None,
    scheduler_config_path: Path | None = None,
    scheduler_factory: SchedulerFactory | None = None,
    wait_forever: WaitForever | None = None,
) -> None:
    """Run startup export, register hourly export, and keep the service alive."""
    config_path = scheduler_config_path or Path(config.SCHEDULER_CONFIG_PATH)
    resolved_config = scheduler_config or load_scheduler_config(config_path)
    startup_job = next((job for job in resolved_config.jobs if job.enabled), None)
    startup_exporter = (exporter or build_exporter(startup_job)) if startup_job else None
    logger.debug("Loaded scoring scheduler config: timezone=%s jobs=%s", resolved_config.timezone, resolved_config.jobs)

    if startup_exporter is not None:
        logger.debug("Running startup export using job config: %s", startup_job)
        await run_startup_export(exporter=startup_exporter)
    else:
        logger.info("No enabled scoring jobs configured for startup export")

    scheduler = (scheduler_factory or build_scheduler)(resolved_config.timezone)
    for job_config in resolved_config.jobs:
        if not job_config.enabled:
            logger.info("Skipping disabled scoring job %s", job_config.name)
            continue
        logger.debug("Registering scoring job config: %s", job_config)
        add_hourly_export_job(scheduler, job_config=job_config, exporter=exporter or build_exporter(job_config))
    scheduler.start()
    logger.info("Scoring scheduler started with %s job(s)", len(scheduler.get_jobs()))

    try:
        await (wait_forever or wait_until_cancelled)()
    finally:
        scheduler.shutdown(wait=False)


async def run_startup_export(*, exporter: Exporter = export_recent_readings_csv) -> None:
    """Run one export at service startup and log failures without raising."""
    try:
        output_path = await exporter()
    except Exception:
        logger.exception("Startup hourly scoring export failed")
        return

    logger.info("Startup hourly scoring export wrote %s", output_path)


def build_scheduler(timezone: str):
    """Build the APScheduler instance for hourly scoring exports."""
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
    except ModuleNotFoundError as error:
        message = "APScheduler is required for the scoring scheduler service. Install service requirements."
        raise RuntimeError(message) from error

    return AsyncIOScheduler(timezone=timezone)


def build_exporter(job_config: ScheduledScoringJobConfig | None) -> Exporter:
    """Build an exporter callable from scheduler config.

    Each invocation re-reads the promotion marker (once per scoring run) so a
    freshly promoted model is picked up without restarting the service. The
    marker takes precedence over YAML-pinned ``model_*`` fields; if it is
    absent/malformed the loader falls back to the env-pinned defaults.
    """
    if job_config is None:
        return export_recent_readings_csv

    async def configured_exporter():
        promoted = load_promoted_model()
        logger.debug(
            "Running configured hourly exporter: output_base_dir=%s lookback_hours=%s "
            "model_run_id=%s model_config_name=%s model_source=%s",
            job_config.output_base_dir,
            job_config.lookback_hours,
            promoted.run_id,
            promoted.config_name,
            promoted.source,
        )
        return await export_recent_readings_csv(
            output_base_dir=job_config.output_base_dir,
            lookback=timedelta(hours=job_config.lookback_hours),
            offset=timedelta(hours=job_config.offset_hours),
            feature_context=timedelta(hours=job_config.feature_context_hours),
            model_artifact_dir=promoted.artifact_dir,
            model_run_id=promoted.run_id,
            model_config_name=promoted.config_name,
        )

    return configured_exporter


def add_hourly_export_job(
    scheduler,
    *,
    job_config: ScheduledScoringJobConfig | None = None,
    exporter: Exporter = export_recent_readings_csv,
) -> None:
    """Register the hourly CSV export job."""
    resolved_job_config = job_config or ScheduledScoringJobConfig(
        name=HOURLY_EXPORT_JOB_ID,
        job_type="hourly_recent_readings_csv_export",
        enabled=True,
        trigger="interval",
        output_base_dir=Path(config.HOURLY_SCORING_OUTPUT_DIR),
        lookback_hours=config.HOURLY_SCORING_LOOKBACK_HOURS,
        offset_hours=config.HOURLY_SCORING_OFFSET_HOURS,
        feature_context_hours=config.FEATURE_CONTEXT_HOURS,
        model_artifact_dir=Path(config.MODEL_ARTIFACT_DIR),
        model_run_id=config.MODEL_RUN_ID,
        model_config_name=config.MODEL_CONFIG_NAME,
        hours=1,
    )
    scheduler.add_job(
        exporter,
        trigger=resolved_job_config.trigger,
        id=resolved_job_config.name,
        name="Hourly recent readings CSV export",
        replace_existing=True,
        **build_trigger_args(resolved_job_config),
    )
    logger.info("Scheduled %s with %s trigger", resolved_job_config.name, resolved_job_config.trigger)


def build_trigger_args(job_config: ScheduledScoringJobConfig) -> dict[str, int]:
    """Build APScheduler interval trigger arguments."""
    return {
        key: value
        for key, value in {
            "seconds": job_config.seconds,
            "minutes": job_config.minutes,
            "hours": job_config.hours,
        }.items()
        if value is not None
    }


async def wait_until_cancelled() -> None:
    """Wait forever until the service is cancelled or stopped."""
    await asyncio.Event().wait()
