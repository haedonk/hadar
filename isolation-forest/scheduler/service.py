import argparse
import asyncio
import sys
from pathlib import Path

ISOLATION_FOREST_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ISOLATION_FOREST_DIR.parent
for path in (str(ISOLATION_FOREST_DIR), str(PROJECT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from scheduler.config import ScheduledJobConfig, load_scheduler_config  # noqa: E402
from scheduler.jobs import run_training_sweep_job  # noqa: E402
from utils.logger import get_logger, setup_logging  # noqa: E402

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the HADAR scheduler service.")
    parser.add_argument(
        "--config",
        type=Path,
        default=ISOLATION_FOREST_DIR / "configs" / "scheduler" / "scheduler.yaml",
        help="Path to the scheduler YAML config.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    setup_logging()
    scheduler_config = load_scheduler_config(args.config)
    scheduler = _build_scheduler(scheduler_config.timezone)

    for job_config in scheduler_config.jobs:
        if not job_config.enabled:
            logger.info("Skipping disabled scheduled job %s", job_config.name)
            continue
        _add_job(scheduler, job_config)

    scheduler.start()
    logger.info("Scheduler started with %s enabled job(s)", len(scheduler.get_jobs()))

    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown(wait=False)


def _build_scheduler(timezone: str):
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
    except ModuleNotFoundError as error:
        message = "APScheduler is required for the scheduler service. Install project requirements."
        raise RuntimeError(message) from error

    return AsyncIOScheduler(timezone=timezone)


def _add_job(scheduler, job_config: ScheduledJobConfig) -> None:
    trigger_args = _build_trigger_args(job_config)
    scheduler.add_job(
        run_training_sweep_job,
        trigger=job_config.trigger,
        id=job_config.name,
        name=job_config.name,
        replace_existing=True,
        kwargs={"config_path": job_config.config_path},
        **trigger_args,
    )
    logger.info("Scheduled %s with %s trigger: %s", job_config.name, job_config.trigger, trigger_args)


def _build_trigger_args(job_config: ScheduledJobConfig) -> dict:
    if job_config.trigger == "cron":
        args = {"hour": job_config.hour, "minute": job_config.minute or 0}
        if job_config.day_of_week is not None:
            args["day_of_week"] = job_config.day_of_week
        return args

    return {
        key: value
        for key, value in {
            "seconds": job_config.seconds,
            "minutes": job_config.minutes,
            "hours": job_config.hours,
        }.items()
        if value is not None
    }


if __name__ == "__main__":
    asyncio.run(main())
