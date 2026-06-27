from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import JobStatus, SceneStatus
from app.db.session import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(300))
    hook: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default=JobStatus.QUEUED.value, index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(16), default="es")
    aspect_ratio: Mapped[str] = mapped_column(String(16), default="16:9")
    duration_seconds: Mapped[int] = mapped_column(Integer, default=60)
    scene_duration_seconds: Mapped[int] = mapped_column(Integer, default=4)
    scene_count: Mapped[int] = mapped_column(Integer, default=15)
    width: Mapped[int] = mapped_column(Integer, default=1280)
    height: Mapped[int] = mapped_column(Integer, default=720)
    fps: Mapped[int] = mapped_column(Integer, default=25)
    final_video_path: Mapped[str | None] = mapped_column(Text)
    script_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    scenes: Mapped[list["Scene"]] = relationship(back_populates="job", cascade="all, delete-orphan", order_by="Scene.scene_number")


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    scene_number: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(40), default=SceneStatus.PENDING.value, index=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=4)
    visual_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    narration: Mapped[str] = mapped_column(Text, nullable=False)
    subtitle: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_id: Mapped[str | None] = mapped_column(String(120))
    audio_prompt_id: Mapped[str | None] = mapped_column(String(120))
    seed: Mapped[int | None] = mapped_column(Integer)
    video_path: Mapped[str | None] = mapped_column(Text)
    audio_path: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    audio_error: Mapped[str | None] = mapped_column(Text)
    generation_seconds: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    job: Mapped[Job] = relationship(back_populates="scenes")
