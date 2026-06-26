from app.core.enums import JobStatus, SceneStatus


def test_job_status_values() -> None:
    assert {status.value for status in JobStatus} == {
        "queued",
        "planning",
        "generating_video",
        "generating_audio",
        "assembling",
        "completed",
        "failed",
        "cancelled",
    }


def test_scene_status_values() -> None:
    assert {status.value for status in SceneStatus} == {"pending", "generating", "completed", "failed", "skipped"}
