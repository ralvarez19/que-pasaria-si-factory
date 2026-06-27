import json
from pathlib import Path

from app.core.config import Settings
from app.models.job import Job
from app.schemas.planning import ContentPlan


JOB_DIRS = ("scenes", "clips", "audio", "subtitles", "temp", "final", "logs")


def ensure_job_dirs(settings: Settings, job_id: str) -> Path:
    root = settings.jobs_dir / job_id
    root.mkdir(parents=True, exist_ok=True)
    for dirname in JOB_DIRS:
        (root / dirname).mkdir(parents=True, exist_ok=True)
    return root


def write_job_snapshot(settings: Settings, job: Job) -> None:
    root = ensure_job_dirs(settings, job.id)
    payload = {
        "id": job.id,
        "topic": job.topic,
        "status": job.status,
        "title": job.title,
        "hook": job.hook,
        "error_message": job.error_message,
        "duration_seconds": job.duration_seconds,
        "scene_duration_seconds": job.scene_duration_seconds,
        "scene_count": job.scene_count,
        "width": job.width,
        "height": job.height,
        "fps": job.fps,
        "final_video_path": job.final_video_path,
        "script_path": job.script_path,
        "telegram_status": job.telegram_status,
        "telegram_error": job.telegram_error,
        "telegram_sent_at": job.telegram_sent_at.isoformat() if job.telegram_sent_at else None,
        "telegram_message_id": job.telegram_message_id,
    }
    (root / "job.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_script(settings: Settings, job_id: str, plan: ContentPlan) -> Path:
    root = ensure_job_dirs(settings, job_id)
    script_path = root / "script.json"
    script_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    return script_path


def scene_clip_path(settings: Settings, job_id: str, scene_number: int) -> Path:
    return settings.jobs_dir / job_id / "clips" / f"scene_{scene_number:03d}.mp4"


def scene_audio_path(settings: Settings, job_id: str, scene_number: int) -> Path:
    extension = settings.tts_audio_format.strip().lstrip(".") or "wav"
    return settings.jobs_dir / job_id / "audio" / f"scene_{scene_number:03d}.{extension}"
