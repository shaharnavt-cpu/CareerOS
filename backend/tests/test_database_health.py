"""Database health and structured connectivity failure tests."""

from __future__ import annotations

import logging

from sqlalchemy.exc import OperationalError

from app.services.database_health import (
    DatabaseHealthMonitor,
    classify_database_failure,
)


class FailingEngine:
    def connect(self):
        raise OperationalError(
            "connect",
            {},
            TimeoutError("connection timeout to localhost:5432"),
        )


def test_timeout_is_structured_without_losing_developer_detail() -> None:
    error = OperationalError(
        "connect", {}, TimeoutError("connection timeout to localhost:5432")
    )

    failure = classify_database_failure(error)

    assert failure.code == "DATABASE_TIMEOUT"
    assert "parsed document is safe" in failure.friendly_message
    assert "localhost:5432" in failure.developer_message
    assert "OperationalError" in failure.stack_trace


def test_health_monitor_warns_and_hides_diagnostics_by_default(caplog) -> None:
    monitor = DatabaseHealthMonitor(minimum_check_interval_seconds=0)

    with caplog.at_level(logging.WARNING):
        result = monitor.check(FailingEngine())

    assert result["status"] == "unavailable"
    assert result["error_code"] == "DATABASE_TIMEOUT"
    assert "developer_message" not in result
    assert "PostgreSQL startup health check failed" in caplog.text

    developer = monitor.snapshot(developer=True)
    assert "localhost:5432" in developer["developer_message"]
    assert developer["stack_trace"]
