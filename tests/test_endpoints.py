from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_jobs_list_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/jobs")

    assert response.status_code == 200
    assert "jobs" in response.json()
