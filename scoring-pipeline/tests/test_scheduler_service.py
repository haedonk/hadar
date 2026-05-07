import pytest

from scheduler.config import ScheduledScoringJobConfig, ScoringSchedulerConfig
from scheduler.service import (
    HOURLY_EXPORT_JOB_ID,
    add_hourly_export_job,
    build_trigger_args,
    run_scoring_service,
    run_startup_export,
)


class FakeScheduler:
    def __init__(self) -> None:
        self.jobs = []
        self.started = False
        self.shutdown_calls = []

    def add_job(self, func, **kwargs) -> None:
        self.jobs.append({"func": func, **kwargs})

    def start(self) -> None:
        self.started = True

    def get_jobs(self):
        return self.jobs

    def shutdown(self, wait: bool = True) -> None:
        self.shutdown_calls.append(wait)


@pytest.mark.asyncio
async def test_run_startup_export_invokes_exporter() -> None:
    calls = []

    async def exporter():
        calls.append("called")
        return "/tmp/recent_readings.csv"

    await run_startup_export(exporter=exporter)

    assert calls == ["called"]


@pytest.mark.asyncio
async def test_run_startup_export_logs_failure_without_raising() -> None:
    async def exporter():
        raise RuntimeError("export failed")

    await run_startup_export(exporter=exporter)


def test_add_hourly_export_job_registers_interval_job() -> None:
    scheduler = FakeScheduler()
    job_config = ScheduledScoringJobConfig(
        name=HOURLY_EXPORT_JOB_ID,
        job_type="hourly_recent_readings_csv_export",
        enabled=True,
        trigger="interval",
        output_base_dir="/tmp/hourly-scoring-runs",
        lookback_hours=1,
        offset_hours=1,
        hours=1,
    )

    async def exporter():
        return None

    add_hourly_export_job(scheduler, job_config=job_config, exporter=exporter)

    assert len(scheduler.jobs) == 1
    job = scheduler.jobs[0]
    assert job["func"] is exporter
    assert job["trigger"] == "interval"
    assert job["hours"] == 1
    assert job["id"] == HOURLY_EXPORT_JOB_ID
    assert job["replace_existing"] is True


@pytest.mark.asyncio
async def test_run_scoring_service_runs_startup_export_and_registers_scheduler() -> None:
    calls = []
    scheduler = FakeScheduler()
    scheduler_config = ScoringSchedulerConfig(
        timezone="America/New_York",
        jobs=[
            ScheduledScoringJobConfig(
                name=HOURLY_EXPORT_JOB_ID,
                job_type="hourly_recent_readings_csv_export",
                enabled=True,
                trigger="interval",
                output_base_dir="/tmp/hourly-scoring-runs",
                lookback_hours=1,
                offset_hours=1,
                hours=1,
            )
        ],
    )

    async def exporter():
        calls.append("export")
        return "/tmp/recent_readings.csv"

    def scheduler_factory(timezone: str):
        assert timezone == "America/New_York"
        return scheduler

    async def wait_once():
        calls.append("wait")

    await run_scoring_service(
        exporter=exporter,
        scheduler_config=scheduler_config,
        scheduler_factory=scheduler_factory,
        wait_forever=wait_once,
    )

    assert calls == ["export", "wait"]
    assert scheduler.started is True
    assert len(scheduler.jobs) == 1
    assert scheduler.jobs[0]["id"] == HOURLY_EXPORT_JOB_ID
    assert scheduler.shutdown_calls == [False]


@pytest.mark.asyncio
async def test_run_scoring_service_schedules_even_if_startup_export_fails() -> None:
    scheduler = FakeScheduler()
    scheduler_config = ScoringSchedulerConfig(
        timezone="America/New_York",
        jobs=[
            ScheduledScoringJobConfig(
                name=HOURLY_EXPORT_JOB_ID,
                job_type="hourly_recent_readings_csv_export",
                enabled=True,
                trigger="interval",
                output_base_dir="/tmp/hourly-scoring-runs",
                lookback_hours=1,
                offset_hours=1,
                hours=1,
            )
        ],
    )

    async def exporter():
        raise RuntimeError("export failed")

    async def wait_once():
        return None

    await run_scoring_service(
        exporter=exporter,
        scheduler_config=scheduler_config,
        scheduler_factory=lambda timezone: scheduler,
        wait_forever=wait_once,
    )

    assert scheduler.started is True
    assert len(scheduler.jobs) == 1
    assert scheduler.shutdown_calls == [False]


@pytest.mark.asyncio
async def test_run_scoring_service_skips_disabled_jobs() -> None:
    scheduler = FakeScheduler()
    scheduler_config = ScoringSchedulerConfig(
        timezone="America/New_York",
        jobs=[
            ScheduledScoringJobConfig(
                name=HOURLY_EXPORT_JOB_ID,
                job_type="hourly_recent_readings_csv_export",
                enabled=False,
                trigger="interval",
                output_base_dir="/tmp/hourly-scoring-runs",
                lookback_hours=1,
                offset_hours=1,
                hours=1,
            )
        ],
    )

    async def exporter():
        raise AssertionError("disabled jobs should not run")

    async def wait_once():
        return None

    await run_scoring_service(
        exporter=exporter,
        scheduler_config=scheduler_config,
        scheduler_factory=lambda timezone: scheduler,
        wait_forever=wait_once,
    )

    assert scheduler.started is True
    assert scheduler.jobs == []
    assert scheduler.shutdown_calls == [False]


def test_build_trigger_args_uses_configured_interval_fields() -> None:
    job_config = ScheduledScoringJobConfig(
        name=HOURLY_EXPORT_JOB_ID,
        job_type="hourly_recent_readings_csv_export",
        enabled=True,
        trigger="interval",
        output_base_dir="/tmp/hourly-scoring-runs",
        lookback_hours=1,
        offset_hours=1,
        minutes=30,
    )

    assert build_trigger_args(job_config) == {"minutes": 30}
