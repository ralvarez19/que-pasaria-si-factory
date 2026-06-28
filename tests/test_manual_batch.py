import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.db.session import SessionLocal, init_db
from app.models.job import Job
from app.services.batch.manual_script_batch_runner import ManualScriptBatchRunner
from app.services.script_quality import load_manual_script


class FakeBatchWorker:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.created_jobs: list[str] = []

    def create_job_from_script(self, db, script_path: Path) -> Job:
        manual = load_manual_script(script_path)
        job = Job(
            id=str(uuid4()),
            topic=manual.topic,
            title=manual.title,
            status="queued",
            duration_seconds=manual.duration_seconds,
            scene_duration_seconds=manual.scene_duration_seconds,
            scene_count=len(manual.plan.scenes),
            width=manual.width,
            height=manual.height,
            fps=manual.fps,
            script_path=str(script_path),
            telegram_status="pending",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        self.created_jobs.append(job.id)
        return job

    async def enqueue(self, job_id: str) -> None:
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            assert job is not None
            final_path = self.settings.jobs_dir / job_id / "final" / "final.mp4"
            latest_path = self.settings.data_dir / "outputs" / "latest" / "final.mp4"
            archive_path = self.settings.data_dir / "outputs" / "archive" / f"{job_id[:8]}.mp4"
            job.status = "completed"
            job.final_video_path = str(final_path)
            job.latest_video_path = str(latest_path)
            job.archive_video_path = str(archive_path)
            job.telegram_status = "sent"
            job.telegram_error = None
            db.commit()


@pytest.mark.asyncio
async def test_batch_processes_two_valid_json_files(tmp_path: Path) -> None:
    runner, pending = make_runner(tmp_path)
    write_batch_script(pending / "01_luna.json")
    write_batch_script(pending / "02_sol.json", topic="¿Qué pasaría si el Sol se apagara?")

    summary = await runner.run_batch(pending)

    assert summary["processed_count"] == 2
    assert summary["failed_count"] == 0
    assert len(list((pending.parent / "done").glob("*.json"))) == 4  # 2 scripts + 2 result files
    assert not list(pending.glob("*.json"))


@pytest.mark.asyncio
async def test_batch_continues_after_invalid_when_stop_on_error_false(tmp_path: Path) -> None:
    runner, pending = make_runner(tmp_path)
    write_invalid_script(pending / "01_bad.json")
    write_batch_script(pending / "02_luna.json")

    summary = await runner.run_batch(pending, stop_on_error=False)

    assert summary["processed_count"] == 1
    assert summary["failed_count"] == 1
    assert len(list((pending.parent / "failed").glob("*.error.json"))) == 1
    assert len(list((pending.parent / "done").glob("*.result.json"))) == 1


@pytest.mark.asyncio
async def test_batch_moves_processing_to_done_and_writes_result(tmp_path: Path) -> None:
    runner, pending = make_runner(tmp_path)
    write_batch_script(pending / "01_luna.json")

    await runner.run_batch(pending)

    done_results = list((pending.parent / "done").glob("*.result.json"))
    assert len(done_results) == 1
    payload = json.loads(done_results[0].read_text(encoding="utf-8"))
    assert payload["original_filename"] == "01_luna.json"
    assert payload["job_id"]
    assert payload["telegram_status"] == "sent"
    assert not list((pending.parent / "processing").glob("*.json"))


@pytest.mark.asyncio
async def test_batch_moves_processing_to_failed_and_writes_error(tmp_path: Path) -> None:
    runner, pending = make_runner(tmp_path)
    write_invalid_script(pending / "01_bad.json")

    await runner.run_batch(pending)

    failed_errors = list((pending.parent / "failed").glob("*.error.json"))
    assert len(failed_errors) == 1
    payload = json.loads(failed_errors[0].read_text(encoding="utf-8"))
    assert payload["original_filename"] == "01_bad.json"
    assert "scenes" in payload["error_message"]
    assert not list((pending.parent / "processing").glob("*.json"))


def test_batch_does_not_start_twice(tmp_path: Path) -> None:
    runner, pending = make_runner(tmp_path)
    runner.state.running = True

    with pytest.raises(RuntimeError, match="batch manual"):
        runner.start(pending)


@pytest.mark.asyncio
async def test_batch_supports_files_with_different_scene_durations(tmp_path: Path) -> None:
    runner, pending = make_runner(tmp_path)
    write_batch_script(pending / "01_short.json", duration_seconds=20, scene_duration_seconds=4, scene_count=5)
    write_batch_script(pending / "02_long.json", duration_seconds=60, scene_duration_seconds=5, scene_count=12)

    summary = await runner.run_batch(pending)

    assert summary["processed_count"] == 2
    assert summary["failed_count"] == 0


def make_runner(tmp_path: Path) -> tuple[ManualScriptBatchRunner, Path]:
    init_db()
    settings = Settings(data_dir=tmp_path / "data", jobs_dir=tmp_path / "data" / "jobs", log_file=tmp_path / "app.log")
    pending = tmp_path / "data" / "input" / "manual_scripts" / "pending"
    pending.mkdir(parents=True)
    runner = ManualScriptBatchRunner(FakeBatchWorker(settings), poll_interval_seconds=0.01)  # type: ignore[arg-type]
    return runner, pending


def write_batch_script(
    path: Path,
    topic: str = "¿Qué pasaría si la Luna desapareciera?",
    *,
    duration_seconds: int = 4,
    scene_duration_seconds: int = 4,
    scene_count: int = 1,
) -> None:
    scenes = []
    for index in range(scene_count):
        narration = "Imagina que la Luna desaparece, y la Tierra empieza a cambiar en silencio"
        scenes.append(
            {
                "scene_number": index + 1,
                "duration_seconds": scene_duration_seconds,
                "visual_prompt": f"A cinematic realistic view of Earth from space as the Moon fades away scene {index + 1}.",
                "narration": narration,
                "subtitle": narration,
            }
        )
    path.write_text(
        json.dumps(
            {
                "topic": topic,
                "title": topic,
                "duration_seconds": duration_seconds,
                "scene_duration_seconds": scene_duration_seconds,
                "language": "es",
                "aspect_ratio": "16:9",
                "width": 1280,
                "height": 720,
                "fps": 25,
                "scenes": scenes,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def write_invalid_script(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "topic": "¿Qué pasaría si la Luna desapareciera?",
                "title": "¿Qué pasaría si la Luna desapareciera?",
                "duration_seconds": 4,
                "scene_duration_seconds": 4,
                "scenes": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
