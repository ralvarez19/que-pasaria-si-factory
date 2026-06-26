import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.models.job import Job, Scene
from app.schemas.jobs import JobCreate
from app.schemas.planning import ContentPlan, PlannedScene
from app.services.paths import write_job_snapshot, write_script
from app.services.subtitles import generate_srt


UTF8_TEXTS = [
    "¿Qué pasaría si la Luna desapareciera?",
    "El océano cambiaría durante años.",
    "La humanidad tendría nuevas dificultades.",
    "Un niño observó el cielo.",
    "Mañana comenzaría una nueva era.",
]


def assert_no_mojibake(text: str) -> None:
    assert "Â" not in text
    assert "Ã" not in text
    assert "�" not in text


def test_pydantic_preserves_spanish_utf8() -> None:
    request = JobCreate(topic=UTF8_TEXTS[0])
    assert request.topic == UTF8_TEXTS[0]


def test_api_json_response_preserves_spanish_utf8() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/jobs",
            json={"topic": UTF8_TEXTS[0], "duration_seconds": 4, "scene_duration_seconds": 4, "width": 640, "height": 360, "fps": 15},
        )
        job_id = response.json()["job_id"]
        job_response = client.get(f"/api/v1/jobs/{job_id}")

    assert job_response.status_code == 200
    payload = job_response.json()
    assert payload["topic"] == UTF8_TEXTS[0]
    assert_no_mojibake(json.dumps(payload, ensure_ascii=False))


def test_job_and_script_json_are_written_as_utf8(tmp_path: Path) -> None:
    settings = Settings(jobs_dir=tmp_path, log_file=tmp_path / "app.log")
    job = Job(
        id="utf8-job",
        topic=UTF8_TEXTS[0],
        status="queued",
        title=UTF8_TEXTS[0],
        hook=UTF8_TEXTS[1],
        duration_seconds=20,
        scene_duration_seconds=4,
        scene_count=5,
        width=1280,
        height=720,
        fps=25,
    )
    plan = ContentPlan(
        title=UTF8_TEXTS[0],
        hook=UTF8_TEXTS[1],
        scenes=[
            PlannedScene(scene_number=index + 1, duration_seconds=4, visual_prompt=f"documentary scene {index}", narration=text, subtitle=text)
            for index, text in enumerate(UTF8_TEXTS)
        ],
    )

    write_job_snapshot(settings, job)
    write_script(settings, job.id, plan)

    job_text = (tmp_path / "utf8-job" / "job.json").read_text(encoding="utf-8")
    script_text = (tmp_path / "utf8-job" / "script.json").read_text(encoding="utf-8")
    for expected in UTF8_TEXTS:
        assert expected in job_text + script_text
    assert_no_mojibake(job_text + script_text)


def test_srt_preserves_spanish_utf8(tmp_path: Path) -> None:
    scenes = [
        Scene(job_id="utf8-job", scene_number=index + 1, duration_seconds=4, visual_prompt=f"prompt {index}", narration=text, subtitle=text)
        for index, text in enumerate(UTF8_TEXTS)
    ]

    srt_path = generate_srt(scenes, tmp_path / "final.srt")
    srt_text = srt_path.read_text(encoding="utf-8")

    for expected in UTF8_TEXTS:
        assert expected in srt_text
    assert_no_mojibake(srt_text)
