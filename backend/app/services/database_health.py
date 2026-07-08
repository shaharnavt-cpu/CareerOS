"""Database connectivity diagnostics shared by health and listening services."""

from __future__ import annotations

import logging
import threading
import time
import traceback
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache

from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatabaseFailure:
    """Structured database failure safe for pipeline classification."""

    code: str
    friendly_message: str
    developer_message: str
    exception_type: str
    stack_trace: str


def classify_database_failure(error: BaseException) -> DatabaseFailure:
    """Distinguish connection timeouts from other availability failures."""

    developer_message = str(error)
    lowered = developer_message.casefold()
    is_timeout = "timeout" in lowered or "timed out" in lowered
    code = "DATABASE_TIMEOUT" if is_timeout else "DATABASE_UNAVAILABLE"
    friendly = (
        "CareerOS could not reach Career Memory before the connection timed out. "
        "Your parsed document is safe in this process; retry when PostgreSQL is ready."
        if is_timeout
        else "Career Memory is temporarily unavailable. Your parsed document is safe "
        "in this process; retry when PostgreSQL is ready."
    )
    return DatabaseFailure(
        code=code,
        friendly_message=friendly,
        developer_message=developer_message,
        exception_type=type(error).__name__,
        stack_trace="".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        ),
    )


class DatabaseHealthMonitor:
    """Thread-safe, refreshable PostgreSQL health state."""

    def __init__(self, minimum_check_interval_seconds: float = 3.0) -> None:
        self._minimum_interval = minimum_check_interval_seconds
        self._lock = threading.RLock()
        self._status = "unknown"
        self._checked_at: datetime | None = None
        self._checked_monotonic = 0.0
        self._latency_ms: float | None = None
        self._failure: DatabaseFailure | None = None

    @property
    def available(self) -> bool:
        with self._lock:
            return self._status == "available"

    def check(self, engine: Engine, *, force: bool = False) -> dict[str, object]:
        """Check connectivity, caching recent results to avoid health-check pressure."""

        with self._lock:
            fresh = (
                self._checked_at is not None
                and time.monotonic() - self._checked_monotonic < self._minimum_interval
            )
            if fresh and not force:
                return self.snapshot()

        started = time.perf_counter()
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except OperationalError as error:
            failure = classify_database_failure(error)
            self.mark_failure(failure, started=started)
            logger.warning(
                "PostgreSQL startup health check failed: %s. Listening persistence "
                "will remain retryable in memory.",
                failure.code,
            )
        except Exception as error:
            failure = classify_database_failure(error)
            self.mark_failure(failure, started=started)
            logger.warning("Database health check failed: %s", failure.code)
        else:
            self.mark_available(started=started)
        return self.snapshot()

    def mark_available(self, *, started: float | None = None) -> None:
        now = datetime.now(UTC)
        latency = (time.perf_counter() - started) * 1000 if started else None
        with self._lock:
            self._status = "available"
            self._checked_at = now
            self._checked_monotonic = time.monotonic()
            self._latency_ms = round(latency, 2) if latency is not None else None
            self._failure = None

    def mark_failure(
        self, failure: DatabaseFailure, *, started: float | None = None
    ) -> None:
        now = datetime.now(UTC)
        latency = (time.perf_counter() - started) * 1000 if started else None
        with self._lock:
            self._status = "unavailable"
            self._checked_at = now
            self._checked_monotonic = time.monotonic()
            self._latency_ms = round(latency, 2) if latency is not None else None
            self._failure = failure

    def snapshot(self, *, developer: bool = False) -> dict[str, object]:
        with self._lock:
            result: dict[str, object] = {
                "status": self._status,
                "checked_at": self._checked_at,
                "latency_ms": self._latency_ms,
                "error_code": self._failure.code if self._failure else None,
                "message": self._failure.friendly_message if self._failure else None,
            }
            if developer and self._failure:
                result["developer_message"] = self._failure.developer_message
                result["exception_type"] = self._failure.exception_type
                result["stack_trace"] = self._failure.stack_trace
            return result


@lru_cache
def get_database_health() -> DatabaseHealthMonitor:
    return DatabaseHealthMonitor()
