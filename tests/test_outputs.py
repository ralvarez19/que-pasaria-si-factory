from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.session import SessionLocal, init_db
from app.main import app
from app.models.job import Job
from app.providers.planner import MockPlannerProvider
from app.providers.tts import SilentTTSProvider
from app.providers.video import PlaceholderVideoProvider
from app.services.ffmpeg import FFmpegAssembler
from app.services.outputs import copy_final_outputs, latest_video_path
from app.services.telegram import TelegramNotifier, TelegramSendResult
from app.services.worker import JobWorker


class FakeNotifier:
    def __init__(self, results: list[TelegramSendResult]):
        self.results = results
        self.calls: list[Path] = []

    def configuration_error(self) -> str | None:
        return None

    def masked_chat_id(self) -> str:
        return "123...89"

    async def send_video(self, video_path: Path, caption: str) -> TelegramSendResult:
        self.calls.append(video_path)
        return self.results.pop(0)


def make_worker(settings: Settings, notifier) -> JobWorker:
    return JobWorker(
        settings=settings,
        planner=MockPlannerProvider(),
        video_provider=PlaceholderVideoProvider(settings),
        tts_provider=SilentTTSProvider(settings),
        assembler=FFmpegAssembler(settings),
        telegram_notifier=notifier,
    )


def test_copy_final_outputs_writes_latest_and_archive(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "data", jobs_dir=tmp_path / "data" / "jobs", log_file=tmp_path / "app.log")
    final_path = tmp_path / "data" / "jobs" / "job-12345678" / "final" / "final.mp4"
    final_path.parent.mkdir(parents=True)
    final_path.write_bytes(b"mp4")

    copies = copy_final_outputs(
        settings,
        final_path,
        topic="¿Qué pasaría si la Luna desapareciera?",
        job_id="5239344f-aaaa-bbbb-cccc-dddddddddddd",
        created_at=datetime(2026, 6, 27, 6, 52),
    )

    assert copies.latest_path == tmp_path / "data" / "outputs" / "latest" / "final.mp4"
    assert copies.latest_path.read_bytes() == b"mp4"
    assert copies.archive_path.exists()
    assert copies.archive_path.name == "20260627_065200_luna_desapareciera_5239344f.mp4"


@pytest.mark.asyncio
async def test_worker_sends_from_job_final_video_path_and_retries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    init_db()
    settings = Settings(
        data_dir=tmp_path / "data",
        jobs_dir=tmp_path / "data" / "jobs",
        log_file=tmp_path / "app.log",
        telegram_enabled=True,
        telegram_bot_token="123:test",
        telegram_chat_id="123456789",
    )
    video_path = tmp_path / "data" / "jobs" / "retry-job" / "final" / "final.mp4"
    video_path.parent.mkdir(parents=True)
    video_path.write_bytes(b"mp4")
    notifier = FakeNotifier(
        [
            TelegramSendResult(ok=False, status="failed", video_path=str(video_path), error="HTTP 500"),
            TelegramSendResult(ok=True, status="sent", method="sendVideo", video_path=str(video_path), telegram_message_id=77),
        ]
    )
    worker = make_worker(settings, notifier)

    async def no_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr("app.services.worker.asyncio.sleep", no_sleep)
    with SessionLocal() as db:
        existing = db.get(Job, "retry-job")
        if existing:
            db.delete(existing)
            db.commit()
        db.add(
            Job(
                id="retry-job",
                topic="¿Qué pasaría si la Luna desapareciera?",
                title="¿Qué pasaría si la Luna desapareciera?",
                status="completed",
                duration_seconds=4,
                scene_duration_seconds=4,
                scene_count=1,
                width=1280,
                height=720,
                fps=25,
                final_video_path=str(video_path),
                telegram_status="pending",
            )
        )
        db.commit()

        result = await worker.send_telegram_for_job(db, "retry-job")
        job = db.get(Job, "retry-job")
        assert job is not None
        assert result.ok is True
        assert notifier.calls == [video_path.resolve(), video_path.resolve()]
        assert job.status == "completed"
        assert job.telegram_status == "sent"
        assert job.telegram_message_id == 77


@pytest.mark.asyncio
async def test_worker_does_not_mark_job_failed_when_telegram_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    init_db()
    settings = Settings(
        data_dir=tmp_path / "data",
        jobs_dir=tmp_path / "data" / "jobs",
        log_file=tmp_path / "app.log",
        telegram_enabled=True,
        telegram_bot_token="123:test",
        telegram_chat_id="123456789",
    )
    video_path = tmp_path / "data" / "jobs" / "failed-telegram-job" / "final" / "final.mp4"
    video_path.parent.mkdir(parents=True)
    video_path.write_bytes(b"mp4")
    notifier = FakeNotifier(
        [
            TelegramSendResult(ok=False, status="failed", video_path=str(video_path), error="HTTP 500"),
            TelegramSendResult(ok=False, status="failed", video_path=str(video_path), error="HTTP 500"),
        ]
    )
    worker = make_worker(settings, notifier)

    async def no_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr("app.services.worker.asyncio.sleep", no_sleep)
    with SessionLocal() as db:
        existing = db.get(Job, "failed-telegram-job")
        if existing:
            db.delete(existing)
            db.commit()
        db.add(
            Job(
                id="failed-telegram-job",
                topic="¿Qué pasaría si la Luna desapareciera?",
                title="¿Qué pasaría si la Luna desapareciera?",
                status="completed",
                duration_seconds=4,
                scene_duration_seconds=4,
                scene_count=1,
                width=1280,
                height=720,
                fps=25,
                final_video_path=str(video_path),
                telegram_status="pending",
            )
        )
        db.commit()

        result = await worker.send_telegram_for_job(db, "failed-telegram-job")
        job = db.get(Job, "failed-telegram-job")
        assert job is not None
        assert result.ok is False
        assert job.status == "completed"
        assert job.telegram_status == "failed"
        assert job.telegram_error == "HTTP 500"


def test_latest_send_telegram_endpoint(tmp_path: Path) -> None:
    latest = tmp_path / "data" / "outputs" / "latest" / "final.mp4"
    latest.parent.mkdir(parents=True)
    latest.write_bytes(b"mp4")

    with TestClient(app) as client:
        original_worker = app.state.worker

        async def fake_send_latest_telegram(caption: str):
            return TelegramSendResult(ok=True, status="sent", method="sendVideo", video_path=str(latest), telegram_message_id=55)

        fake_worker = SimpleNamespace(
            settings=Settings(data_dir=tmp_path / "data", jobs_dir=tmp_path / "data" / "jobs", log_file=tmp_path / "app.log"),
            telegram_notifier=TelegramNotifier(Settings(telegram_enabled=True, telegram_bot_token="123:test", telegram_chat_id="123456789")),
            send_latest_telegram=fake_send_latest_telegram,
        )
        app.state.worker = fake_worker
        try:
            response = client.post("/api/v1/jobs/latest/send-telegram")
        finally:
            app.state.worker = original_worker

    assert response.status_code == 200
    assert response.json()["telegram_message_id"] == 55
