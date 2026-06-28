import asyncio
import json
import logging
import shutil
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.enums import JobStatus
from app.db.session import SessionLocal
from app.models.job import Job
from app.services.script_quality import validate_manual_script_file
from app.services.worker import JobWorker

logger = logging.getLogger(__name__)


DEFAULT_BATCH_PENDING_DIR = Path("data/input/manual_scripts/pending")


@dataclass(slots=True)
class ManualBatchState:
    running: bool = False
    current_file: str | None = None
    current_job_id: str | None = None
    last_error: str | None = None
    processed_count: int = 0
    failed_count: int = 0
    videos_generated: int = 0
    telegram_sent: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    pending_count: int = 0
    processing_count: int = 0
    done_count: int = 0
    failed_file_count: int = 0
    scripts_dir: str = str(DEFAULT_BATCH_PENDING_DIR)
    stop_on_error: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "current_file": self.current_file,
            "current_job_id": self.current_job_id,
            "last_error": self.last_error,
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "videos_generated": self.videos_generated,
            "telegram_sent": self.telegram_sent,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "pending_count": self.pending_count,
            "processing_count": self.processing_count,
            "done_count": self.done_count,
            "failed_file_count": self.failed_file_count,
            "scripts_dir": self.scripts_dir,
            "stop_on_error": self.stop_on_error,
        }


class ManualScriptBatchRunner:
    def __init__(self, worker: JobWorker, *, poll_interval_seconds: float = 2.0):
        self.worker = worker
        self.poll_interval_seconds = poll_interval_seconds
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self.state = ManualBatchState()

    def start(self, scripts_dir: Path | None = None, *, stop_on_error: bool = False) -> dict[str, Any]:
        if self.state.running:
            raise RuntimeError("Ya hay un batch manual en ejecucion")
        path = Path(scripts_dir or DEFAULT_BATCH_PENDING_DIR)
        self._task = asyncio.create_task(self.run_batch(path, stop_on_error=stop_on_error), name="manual-script-batch")
        self._refresh_counts(path)
        return self.state.as_dict()

    async def run_batch(self, scripts_dir: Path | None = None, *, stop_on_error: bool = False) -> dict[str, Any]:
        if self._lock.locked():
            raise RuntimeError("Ya hay un batch manual en ejecucion")
        async with self._lock:
            pending_dir = Path(scripts_dir or DEFAULT_BATCH_PENDING_DIR)
            dirs = self._ensure_dirs(pending_dir)
            self.state = ManualBatchState(
                running=True,
                started_at=datetime.utcnow().isoformat(),
                scripts_dir=str(pending_dir),
                stop_on_error=stop_on_error,
            )
            self._refresh_counts(pending_dir)
            try:
                for pending_path in sorted(pending_dir.glob("*.json"), key=lambda item: item.name.casefold()):
                    if pending_path.name.endswith((".result.json", ".error.json")):
                        continue
                    should_stop = await self._process_one(pending_path, dirs, stop_on_error)
                    self._refresh_counts(pending_dir)
                    if should_stop:
                        break
            finally:
                self.state.running = False
                self.state.current_file = None
                self.state.current_job_id = None
                self.state.finished_at = datetime.utcnow().isoformat()
                self._refresh_counts(pending_dir)
            return self.state.as_dict()

    def get_status(self, scripts_dir: Path | None = None) -> dict[str, Any]:
        self._refresh_counts(Path(scripts_dir or self.state.scripts_dir or DEFAULT_BATCH_PENDING_DIR))
        return self.state.as_dict()

    async def _process_one(self, pending_path: Path, dirs: dict[str, Path], stop_on_error: bool) -> bool:
        started_at = datetime.utcnow().isoformat()
        original_filename = pending_path.name
        processing_path = dirs["processing"] / pending_path.name
        self.state.current_file = str(pending_path)
        self.state.current_job_id = None
        try:
            shutil.move(str(pending_path), str(processing_path))
            self.state.current_file = str(processing_path)
            validation = validate_manual_script_file(processing_path)
            if not validation.ok:
                raise ValueError("; ".join(validation.errors))

            with SessionLocal() as db:
                job = self.worker.create_job_from_script(db, processing_path)
                job_id = job.id
            self.state.current_job_id = job_id
            await self.worker.enqueue(job_id)
            job = await self._wait_for_job(job_id)
            if job.status != JobStatus.COMPLETED.value:
                raise RuntimeError(job.error_message or f"Job termino con status {job.status}")

            finished_at = datetime.utcnow().isoformat()
            done_path = self._move_with_timestamp(processing_path, dirs["done"], finished_at)
            result_payload = {
                "original_filename": original_filename,
                "job_id": job.id,
                "topic": job.topic,
                "title": job.title,
                "final_video_path": job.final_video_path,
                "latest_video_path": job.latest_video_path,
                "archive_video_path": job.archive_video_path,
                "telegram_status": job.telegram_status,
                "telegram_error": job.telegram_error,
                "warnings": validation.warnings,
                "started_at": started_at,
                "finished_at": finished_at,
            }
            self._write_json(done_path.with_suffix(".result.json"), result_payload)
            self.state.processed_count += 1
            if job.final_video_path:
                self.state.videos_generated += 1
            if job.telegram_status == "sent":
                self.state.telegram_sent += 1
            logger.info("Batch manual procesado: %s job_id=%s", original_filename, job.id)
            return False
        except Exception as exc:
            failed_at = datetime.utcnow().isoformat()
            self.state.failed_count += 1
            self.state.last_error = str(exc)
            logger.exception("Batch manual fallo para %s: %s", original_filename, exc)
            source = processing_path if processing_path.exists() else pending_path
            if source.exists():
                failed_path = self._move_with_timestamp(source, dirs["failed"], failed_at)
            else:
                failed_path = dirs["failed"] / self._timestamped_name(original_filename, failed_at)
            self._write_json(
                failed_path.with_suffix(".error.json"),
                {
                    "original_filename": original_filename,
                    "error_message": str(exc),
                    "traceback": traceback.format_exc(),
                    "started_at": started_at,
                    "failed_at": failed_at,
                },
            )
            return stop_on_error

    async def _wait_for_job(self, job_id: str) -> Job:
        while True:
            with SessionLocal() as db:
                job = db.scalar(select(Job).where(Job.id == job_id))
                if job is None:
                    raise RuntimeError(f"Job no encontrado: {job_id}")
                db.expunge(job)
            if job.status in {JobStatus.FAILED.value, JobStatus.CANCELLED.value}:
                return job
            if job.status == JobStatus.COMPLETED.value and job.telegram_status not in {"pending"}:
                return job
            await asyncio.sleep(self.poll_interval_seconds)

    def _ensure_dirs(self, pending_dir: Path) -> dict[str, Path]:
        base = pending_dir.parent
        dirs = {
            "pending": pending_dir,
            "processing": base / "processing",
            "done": base / "done",
            "failed": base / "failed",
        }
        for path in dirs.values():
            path.mkdir(parents=True, exist_ok=True)
        return dirs

    def _refresh_counts(self, pending_dir: Path) -> None:
        dirs = self._ensure_dirs(pending_dir)
        self.state.pending_count = len(list(dirs["pending"].glob("*.json")))
        self.state.processing_count = len(list(dirs["processing"].glob("*.json")))
        self.state.done_count = len([path for path in dirs["done"].glob("*.json") if not path.name.endswith(".result.json")])
        self.state.failed_file_count = len([path for path in dirs["failed"].glob("*.json") if not path.name.endswith(".error.json")])

    def _move_with_timestamp(self, source: Path, target_dir: Path, iso_timestamp: str) -> Path:
        target = target_dir / self._timestamped_name(source.name, iso_timestamp)
        shutil.move(str(source), str(target))
        return target

    @staticmethod
    def _timestamped_name(filename: str, iso_timestamp: str) -> str:
        stamp = datetime.fromisoformat(iso_timestamp).strftime("%Y%m%d_%H%M")
        return f"{stamp}_{filename}"

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
