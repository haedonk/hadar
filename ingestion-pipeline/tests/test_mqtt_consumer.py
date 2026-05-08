"""Tests for ``ingest.mqtt_consumer``.

Covers the silent-coroutine-failure regression guard (Finding #6 in the
2026-05-07 repo review) and the existing malformed-JSON handling in
``MQTTConsumer.on_message``.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ingest.mqtt_consumer import MQTTConsumer, _log_submission_failure


def _make_msg(topic: str, payload: bytes) -> SimpleNamespace:
    """Build a minimal paho-mqtt message stand-in."""
    return SimpleNamespace(topic=topic, payload=payload)


def _build_consumer() -> MQTTConsumer:
    """Construct an MQTTConsumer with a mocked assignment loop and topic mapper.

    We instantiate the real class (so the codepath under test is genuine) and
    then swap the heavy collaborators for mocks. The assignment loop is
    replaced with a ``MagicMock`` so we can intercept
    ``asyncio.run_coroutine_threadsafe`` calls — paho would otherwise schedule
    real work onto the background event loop.
    """
    consumer = MQTTConsumer(
        host="localhost",
        port=1883,
        user=None,
        password=None,
        base_topic="zigbee2mqtt",
    )
    # Swap the real loop for a mock so run_coroutine_threadsafe doesn't actually
    # schedule anything on a background thread during tests.
    consumer.assignment_loop = MagicMock(name="assignment_loop")
    # Stub the assignment service's submit_event so the inner sync path is
    # exercised without touching the asyncio.Queue.
    consumer.assignment_service = MagicMock(name="assignment_service")
    # Topic mapper: by default, return a plausible event so on_message reaches
    # the run_coroutine_threadsafe submission.
    consumer.topic_mapper = MagicMock(name="topic_mapper")
    consumer.topic_mapper.parse_topic.return_value = {"type": "telemetry"}
    consumer.topic_mapper.should_process_event.return_value = True
    # Topic service: insert_if_not_exists must return a coroutine; we make a
    # harmless one that the (mocked) loop never awaits.
    consumer.topic_service = MagicMock(name="topic_service")

    async def _noop(*_args, **_kwargs):
        return None

    consumer.topic_service.insert_if_not_exists.side_effect = lambda *a, **k: _noop()
    return consumer


# --------------------------------------------------------------------------- #
# Task 2 — malformed JSON path                                                #
# --------------------------------------------------------------------------- #


def test_on_message_malformed_json_does_not_raise_and_logs_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Malformed JSON must be caught, logged, and not propagate.

    This locks in the inner try/except around ``json.loads`` so a future edit
    that removes it will surface here instead of crashing the paho thread in
    production.
    """
    consumer = _build_consumer()

    submitted: list[tuple[object, object]] = []

    def _fake_run_coroutine_threadsafe(coro, loop):
        # Close the coroutine so we don't leak "coroutine was never awaited"
        # warnings during the test run.
        if asyncio.iscoroutine(coro):
            coro.close()
        submitted.append((coro, loop))
        fut: concurrent.futures.Future = concurrent.futures.Future()
        fut.set_result(None)
        return fut

    monkeypatch.setattr(
        "ingest.mqtt_consumer.asyncio.run_coroutine_threadsafe",
        _fake_run_coroutine_threadsafe,
    )

    msg = _make_msg("zigbee2mqtt/0xabc/state", b"this is not json{{{")

    with caplog.at_level(logging.WARNING, logger="ingest.mqtt_consumer"):
        # Must not raise.
        consumer.on_message(client=None, userdata=None, msg=msg)

    # The malformed-JSON branch should have logged a warning naming the topic.
    warnings = [
        rec
        for rec in caplog.records
        if rec.levelno == logging.WARNING
        and "Failed to parse JSON payload" in rec.getMessage()
    ]
    assert warnings, f"expected a JSON-parse warning, got records: {caplog.records!r}"
    assert "zigbee2mqtt/0xabc/state" in warnings[0].getMessage()


# --------------------------------------------------------------------------- #
# Task 3 — submitted-coroutine failures are logged                            #
# --------------------------------------------------------------------------- #


def test_log_submission_failure_logs_exception_from_future(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A future that resolved with an exception must produce an error log.

    This is the unit-level guard the review called out as missing — the
    callback must never silently drop coroutine failures.
    """
    fut: concurrent.futures.Future = concurrent.futures.Future()
    fut.set_exception(RuntimeError("boom from background coroutine"))

    with caplog.at_level(logging.ERROR, logger="ingest.mqtt_consumer"):
        _log_submission_failure(fut, context="topic_service.insert_if_not_exists topic=foo")

    error_records = [rec for rec in caplog.records if rec.levelno == logging.ERROR]
    assert error_records, "expected an error log line for the failing future"
    rec = error_records[0]
    assert "Background coroutine failed" in rec.getMessage()
    assert "topic=foo" in rec.getMessage()
    # The exception type must be attached so tracebacks reach the operator.
    assert rec.exc_info is not None
    assert rec.exc_info[0] is RuntimeError


def test_log_submission_failure_silent_on_success(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A successfully resolved future must not log anything."""
    fut: concurrent.futures.Future = concurrent.futures.Future()
    fut.set_result("ok")

    with caplog.at_level(logging.DEBUG, logger="ingest.mqtt_consumer"):
        _log_submission_failure(fut, context="anything")

    assert caplog.records == [], (
        f"successful future must not log, got: {caplog.records!r}"
    )


def test_on_message_attaches_done_callback_that_logs_failures(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """End-to-end guard: on_message attaches a callback that logs exceptions.

    Submits a well-formed message, captures the future returned to the call
    site, then fails it and asserts the consumer's callback wrote an error
    log. If the ``add_done_callback`` line is removed from on_message the
    failure is swallowed and this test fails.
    """
    consumer = _build_consumer()
    captured_futures: list[concurrent.futures.Future] = []

    def _fake_run_coroutine_threadsafe(coro, loop):
        if asyncio.iscoroutine(coro):
            coro.close()
        fut: concurrent.futures.Future = concurrent.futures.Future()
        captured_futures.append(fut)
        return fut

    monkeypatch.setattr(
        "ingest.mqtt_consumer.asyncio.run_coroutine_threadsafe",
        _fake_run_coroutine_threadsafe,
    )

    msg = _make_msg("zigbee2mqtt/0xabc/state", b'{"state": "ON"}')
    consumer.on_message(client=None, userdata=None, msg=msg)

    # on_message submits the topic_service insert; the future for it must have
    # been captured, and a done_callback must be attached.
    assert captured_futures, "expected on_message to submit at least one coroutine"
    fut = captured_futures[-1]

    with caplog.at_level(logging.ERROR, logger="ingest.mqtt_consumer"):
        # Resolve the future with an exception — the attached callback should
        # synchronously fire and emit an error log.
        fut.set_exception(RuntimeError("simulated db hiccup"))

    error_records = [rec for rec in caplog.records if rec.levelno == logging.ERROR]
    assert error_records, (
        "expected the on_message done-callback to log the coroutine failure; "
        "if this fires, the add_done_callback line was likely removed"
    )
    assert any(
        "Background coroutine failed" in rec.getMessage() for rec in error_records
    )
