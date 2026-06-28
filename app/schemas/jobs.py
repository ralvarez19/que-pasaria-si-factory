from datetime import datetime
from math import ceil

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.enums import JobStatus, SceneStatus


class JobCreate(BaseModel):
    topic: str = Field(min_length=5, max_length=500)
    duration_seconds: int = Field(default=60, gt=0, le=1800)
    scene_duration_seconds: int = Field(default=4, gt=0, le=60)
    language: str = Field(default="es", min_length=2, max_length=16)
    aspect_ratio: str = Field(default="16:9", max_length=16)
    width: int = Field(default=1280, ge=256, le=4096)
    height: int = Field(default=720, ge=256, le=4096)
    fps: int = Field(default=25, ge=1, le=120)
    script_path: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_duration(self) -> "JobCreate":
        if self.duration_seconds < self.scene_duration_seconds:
            raise ValueError("duration_seconds must be greater than or equal to scene_duration_seconds")
        return self

    @property
    def scene_count(self) -> int:
        return int(ceil(self.duration_seconds / self.scene_duration_seconds))


class JobQueuedResponse(BaseModel):
    job_id: str
    status: JobStatus


class ScriptPathRequest(BaseModel):
    script_path: str = Field(default="data/input/manual_script.json", min_length=1, max_length=1000)


class ScriptValidationResponse(BaseModel):
    ok: bool
    script_path: str
    errors: list[str] = []
    warnings: list[str] = []
    scene_count: int = 0
    title: str | None = None
    topic: str | None = None


class ManualBatchRunRequest(BaseModel):
    scripts_dir: str = Field(default="data/input/manual_scripts/pending", min_length=1, max_length=1000)
    stop_on_error: bool = False


class ManualBatchStatusResponse(BaseModel):
    running: bool
    current_file: str | None = None
    current_job_id: str | None = None
    pending_count: int = 0
    processing_count: int = 0
    done_count: int = 0
    failed_file_count: int = 0
    last_error: str | None = None
    processed_count: int = 0
    failed_count: int = 0
    videos_generated: int = 0
    telegram_sent: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    scripts_dir: str
    stop_on_error: bool = False


class SceneResponse(BaseModel):
    id: int
    job_id: str
    scene_number: int
    status: SceneStatus
    duration_seconds: int
    visual_prompt: str
    narration: str
    subtitle: str
    tts_text: str | None = None
    prompt_id: str | None = None
    audio_prompt_id: str | None = None
    seed: int | None = None
    video_path: str | None = None
    audio_path: str | None = None
    error_message: str | None = None
    audio_error: str | None = None
    generation_seconds: float | None = None

    model_config = {"from_attributes": True}


class JobResponse(BaseModel):
    id: str
    topic: str
    title: str | None = None
    hook: str | None = None
    status: JobStatus
    error_message: str | None = None
    language: str
    aspect_ratio: str
    duration_seconds: int
    scene_duration_seconds: int
    scene_count: int
    width: int
    height: int
    fps: int
    final_video_path: str | None = None
    latest_video_path: str | None = None
    archive_video_path: str | None = None
    script_path: str | None = None
    telegram_status: str | None = None
    telegram_error: str | None = None
    telegram_sent_at: datetime | None = None
    telegram_message_id: int | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    jobs: list[JobResponse]


class HealthResponse(BaseModel):
    status: str


class TTSTestRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class TTSTestResponse(BaseModel):
    audio_path: str
    prompt_id: str | None = None


class TelegramSendResponse(BaseModel):
    ok: bool
    status: str
    method: str | None = None
    video_path: str | None = None
    error: str | None = None
    telegram_message_id: int | None = None
