from fastapi.testclient import TestClient
from pathlib import Path
from types import SimpleNamespace

from app.main import app
from app.models.job import Job


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


def test_validate_script_endpoint(tmp_path: Path) -> None:
    script_path = write_endpoint_manual_script(tmp_path)
    with TestClient(app) as client:
        response = client.post("/api/v1/scripts/validate", json={"script_path": str(script_path)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["scene_count"] == 1


def test_jobs_from_script_endpoint_uses_manual_script_without_generation(tmp_path: Path) -> None:
    script_path = write_endpoint_manual_script(tmp_path)

    with TestClient(app) as client:
        original_worker = app.state.worker

        async def fake_enqueue(job_id: str) -> None:
            assert job_id == "manual-endpoint-job"

        def fake_create_job_from_script(db, requested_script_path: Path):
            assert requested_script_path == script_path
            existing = db.get(Job, "manual-endpoint-job")
            if existing:
                db.delete(existing)
                db.commit()
            job = Job(
                id="manual-endpoint-job",
                topic="¿Qué pasaría si la Luna desapareciera?",
                title="¿Qué pasaría si la Luna desapareciera?",
                status="queued",
                duration_seconds=4,
                scene_duration_seconds=4,
                scene_count=1,
                width=1280,
                height=720,
                fps=25,
                script_path=str(script_path),
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            return job

        app.state.worker = SimpleNamespace(create_job_from_script=fake_create_job_from_script, enqueue=fake_enqueue)
        try:
            response = client.post("/api/v1/jobs/from-script", json={"script_path": str(script_path)})
        finally:
            app.state.worker = original_worker

    assert response.status_code == 202
    assert response.json()["job_id"] == "manual-endpoint-job"


def write_endpoint_manual_script(tmp_path: Path) -> Path:
    script_path = tmp_path / "manual_script.json"
    script_path.write_text(
        """
{
  "topic": "¿Qué pasaría si la Luna desapareciera?",
  "title": "¿Qué pasaría si la Luna desapareciera?",
  "duration_seconds": 4,
  "scene_duration_seconds": 4,
  "language": "es",
  "aspect_ratio": "16:9",
  "width": 1280,
  "height": 720,
  "fps": 25,
  "scenes": [
    {
      "scene_number": 1,
      "duration_seconds": 4,
      "visual_prompt": "A cinematic realistic view of planet Earth from space as the Moon slowly fades away.",
      "narration": "Imagina que la Luna desaparece, y la Tierra empieza a cambiar en silencio",
      "subtitle": "Imagina que la Luna desaparece, y la Tierra empieza a cambiar en silencio"
    }
  ]
}
""",
        encoding="utf-8",
    )
    return script_path
