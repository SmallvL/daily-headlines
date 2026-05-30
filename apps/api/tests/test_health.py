from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "ok"
    assert "version" in data
    assert "checks" in data
    assert data["checks"]["database"] == "ok"
    assert "uptime_seconds" in data


def test_metrics() -> None:
    response = client.get("/api/metrics")

    assert response.status_code == 200
    data = response.json()["data"]
    assert "uptime_seconds" in data
    assert "requests" in data
    assert "total" in data["requests"]
    assert "errors" in data["requests"]
    assert "avg_response_ms" in data["requests"]
    assert "timestamp" in data
    assert "version" in data
