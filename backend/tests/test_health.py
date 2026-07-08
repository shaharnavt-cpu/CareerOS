"""Tests for the API health endpoint."""

from fastapi.testclient import TestClient

from app.api import health as health_api
from app.main import app

client = TestClient(app)


class StubDatabaseHealth:
    def __init__(self) -> None:
        self.checks: list[tuple[object, bool]] = []

    def check(self, engine: object, *, force: bool = False) -> dict[str, object]:
        self.checks.append((engine, force))
        return self.snapshot()

    def snapshot(self, *, developer: bool = False) -> dict[str, object]:
        result: dict[str, object] = {
            "status": "available",
            "checked_at": None,
            "latency_ms": 1.25,
            "error_code": None,
            "message": None,
        }
        if developer:
            result["developer_message"] = "database diagnostic"
        return result


def test_health_checks_database_and_hides_diagnostics(monkeypatch) -> None:
    monitor = StubDatabaseHealth()
    stub_engine = object()
    monkeypatch.setattr(health_api, "get_database_health", lambda: monitor)
    monkeypatch.setattr(health_api, "engine", stub_engine)

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["api"] == "available"
    assert body["status"] == "ok"
    assert body["database"]["status"] == "available"
    assert "developer_message" not in body["database"]
    assert monitor.checks == [(stub_engine, False)]

    developer = client.get("/api/health?developer=true&refresh=true")

    assert developer.json()["database"]["developer_message"] == "database diagnostic"
    assert monitor.checks[-1] == (stub_engine, True)
