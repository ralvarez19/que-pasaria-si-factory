from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.session import SessionLocal
from app.main import app
from app.models.job import Job
from app.services.telegram import TelegramNotifier, TelegramSendResult


class FakeTelegramResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> dict:
        return self._payload


class FakeAsyncClient:
    responses: list[FakeTelegramResponse] = []
    calls: list[str] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url: str, *args, **kwargs):
        self.calls.append(url)
        return self.responses.pop(0)


def telegram_settings(**overrides) -> Settings:
    values = {
        "telegram_enabled": True,
        "telegram_bot_token": "123:test-token",
        "telegram_chat_id": "123456789",
        "telegram_send_as_video": True,
    }
    values.update(overrides)
    return Settings(**values)


@pytest.mark.asyncio
async def test_telegram_disabled(tmp_path: Path) -> None:
    notifier = TelegramNotifier(telegram_settings(telegram_enabled=False))

    result = await notifier.send_video(tmp_path / "missing.mp4", "caption")

    assert result.ok is False
    assert result.status == "disabled"
    assert result.error == "Telegram deshabilitado"


@pytest.mark.asyncio
async def test_telegram_missing_token(tmp_path: Path) -> None:
    notifier = TelegramNotifier(telegram_settings(telegram_bot_token=""))

    result = await notifier.send_video(tmp_path / "missing.mp4", "caption")

    assert result.ok is False
    assert result.status == "failed"
    assert result.error == "Falta TELEGRAM_BOT_TOKEN"


@pytest.mark.asyncio
async def test_telegram_missing_chat_id(tmp_path: Path) -> None:
    notifier = TelegramNotifier(telegram_settings(telegram_chat_id=""))

    result = await notifier.send_video(tmp_path / "missing.mp4", "caption")

    assert result.ok is False
    assert result.status == "failed"
    assert result.error == "Falta TELEGRAM_CHAT_ID"


@pytest.mark.asyncio
async def test_telegram_missing_file(tmp_path: Path) -> None:
    notifier = TelegramNotifier(telegram_settings())

    result = await notifier.send_video(tmp_path / "missing.mp4", "caption")

    assert result.ok is False
    assert result.status == "failed"
    assert "no existe" in result.error


@pytest.mark.asyncio
async def test_telegram_success_simulated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    video_path = tmp_path / "final.mp4"
    video_path.write_bytes(b"fake video")
    FakeAsyncClient.responses = [FakeTelegramResponse(200, {"ok": True, "result": {"message_id": 42}})]
    FakeAsyncClient.calls = []
    monkeypatch.setattr("app.services.telegram.notifier.httpx.AsyncClient", FakeAsyncClient)

    result = await TelegramNotifier(telegram_settings()).send_video(video_path, "caption")

    assert result.ok is True
    assert result.status == "sent"
    assert result.method == "sendVideo"
    assert result.telegram_message_id == 42
    assert FakeAsyncClient.calls[0].endswith("/sendVideo")


@pytest.mark.asyncio
async def test_telegram_http_error_falls_back_to_document(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    video_path = tmp_path / "final.mp4"
    video_path.write_bytes(b"fake video")
    FakeAsyncClient.responses = [
        FakeTelegramResponse(400, {"ok": False, "description": "Bad Request: wrong file identifier"}),
        FakeTelegramResponse(200, {"ok": True, "result": {"message_id": 43}}),
    ]
    FakeAsyncClient.calls = []
    monkeypatch.setattr("app.services.telegram.notifier.httpx.AsyncClient", FakeAsyncClient)

    result = await TelegramNotifier(telegram_settings()).send_video(video_path, "caption")

    assert result.ok is True
    assert result.method == "sendDocument"
    assert FakeAsyncClient.calls[0].endswith("/sendVideo")
    assert FakeAsyncClient.calls[1].endswith("/sendDocument")


def test_manual_send_telegram_endpoint(tmp_path: Path) -> None:
    video_path = tmp_path / "final.mp4"
    video_path.write_bytes(b"fake video")
    job_id = "telegram-endpoint-job"

    with TestClient(app) as client:
        with SessionLocal() as db:
            existing = db.get(Job, job_id)
            if existing:
                db.delete(existing)
                db.commit()
            db.add(
                Job(
                    id=job_id,
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
                )
            )
            db.commit()

        original_worker = app.state.worker

        async def fake_send_telegram_for_job(db, requested_job_id: str):
            assert requested_job_id == job_id
            return TelegramSendResult(ok=True, status="sent", method="sendVideo", video_path=str(video_path), telegram_message_id=99)

        fake_worker = SimpleNamespace(
            settings=telegram_settings(jobs_dir=tmp_path / "jobs", log_file=tmp_path / "app.log"),
            telegram_notifier=TelegramNotifier(telegram_settings()),
            send_telegram_for_job=fake_send_telegram_for_job,
        )
        app.state.worker = fake_worker
        try:
            response = client.post(f"/api/v1/jobs/{job_id}/send-telegram")
        finally:
            app.state.worker = original_worker

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["status"] == "sent"
    assert payload["telegram_message_id"] == 99
