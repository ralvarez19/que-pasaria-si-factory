import pytest
from pydantic import ValidationError

from app.schemas.jobs import JobCreate


def test_job_create_calculates_scene_count() -> None:
    request = JobCreate(topic="¿Qué pasaría si el Sol se apagara?", duration_seconds=60, scene_duration_seconds=4)
    assert request.scene_count == 15


def test_job_create_rejects_invalid_duration() -> None:
    with pytest.raises(ValidationError):
        JobCreate(topic="Tema valido", duration_seconds=2, scene_duration_seconds=4)
