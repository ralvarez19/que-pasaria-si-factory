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


class SceneResponse(BaseModel):
    id: int
    job_id: str
    scene_number: int
    status: SceneStatus
    duration_seconds: int
    visual_prompt: str
    narration: str
    subtitle: str
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
