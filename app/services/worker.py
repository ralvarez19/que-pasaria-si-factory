import asyncio
import logging
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.core.enums import JobStatus, SceneStatus
from app.core.logging import get_job_logger
from app.db.session import SessionLocal
from app.models.job import Job, Scene
from app.providers.planner import PlannerProvider
from app.providers.tts import TTSProvider
from app.providers.video import VideoProvider
from app.schemas.jobs import JobCreate
from app.services.ffmpeg import FFmpegAssembler
from app.services.paths import ensure_job_dirs, scene_audio_path, scene_clip_path, write_job_snapshot, write_script
from app.services.subtitles import generate_srt

logger = logging.getLogger(__name__)


class JobWorker:
    def __init__(
        self,
        *,
        settings: Settings,
        planner: PlannerProvider,
        video_provider: VideoProvider,
        tts_provider: TTSProvider,
        assembler: FFmpegAssembler,
    ):
        self.settings = settings
        self.planner = planner
        self.video_provider = video_provider
        self.tts_provider = tts_provider
        self.assembler = assembler
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()

    async def start(self) -> None:
        self._recover_incomplete_jobs()
        self._enqueue_existing()
        self.task = asyncio.create_task(self._run(), name="job-worker")

    async def stop(self) -> None:
        self._stopping.set()
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def enqueue(self, job_id: str) -> None:
        await self.queue.put(job_id)

    def create_job(self, db: Session, request: JobCreate) -> Job:
        job = Job(
            id=str(uuid4()),
            topic=request.topic,
            status=JobStatus.QUEUED.value,
            language=request.language,
            aspect_ratio=request.aspect_ratio,
            duration_seconds=request.duration_seconds,
            scene_duration_seconds=request.scene_duration_seconds,
            scene_count=request.scene_count,
            width=request.width,
            height=request.height,
            fps=request.fps,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        ensure_job_dirs(self.settings, job.id)
        write_job_snapshot(self.settings, job)
        return job

    def _recover_incomplete_jobs(self) -> None:
        with SessionLocal() as db:
            statuses = [
                JobStatus.PLANNING.value,
                JobStatus.GENERATING_VIDEO.value,
                JobStatus.GENERATING_AUDIO.value,
                JobStatus.ASSEMBLING.value,
            ]
            jobs = db.scalars(select(Job).where(Job.status.in_(statuses))).all()
            for job in jobs:
                job.status = JobStatus.FAILED.value
                job.error_message = "La API se reinicio mientras el trabajo estaba en proceso. Usa /retry para reintentarlo."
                for scene in job.scenes:
                    if scene.status == SceneStatus.GENERATING.value:
                        scene.status = SceneStatus.FAILED.value
                        scene.error_message = "Interrumpida por reinicio de la API."
                write_job_snapshot(self.settings, job)
            db.commit()

    def _enqueue_existing(self) -> None:
        with SessionLocal() as db:
            queued = db.scalars(select(Job.id).where(Job.status == JobStatus.QUEUED.value)).all()
        for job_id in queued:
            self.queue.put_nowait(job_id)

    async def _run(self) -> None:
        while not self._stopping.is_set():
            job_id = await self.queue.get()
            try:
                await self._process(job_id)
            except Exception:
                logger.exception("Unhandled worker error for job %s", job_id)
            finally:
                self.queue.task_done()

    async def _process(self, job_id: str) -> None:
        job_logger = get_job_logger(job_id, self.settings.jobs_dir)
        job_logger.info("Inicio del trabajo")
        with SessionLocal() as db:
            job = db.scalar(select(Job).where(Job.id == job_id).options(selectinload(Job.scenes)))
            if job is None or job.status in {JobStatus.CANCELLED.value, JobStatus.COMPLETED.value}:
                return
            try:
                await self._plan(db, job, job_logger)
                if self._is_cancelled(db, job.id):
                    return
                await self._generate_video(db, job.id, job_logger)
                if self._is_cancelled(db, job.id):
                    return
                await self._generate_audio(db, job.id, job_logger)
                if self._is_cancelled(db, job.id):
                    return
                await self._assemble(db, job.id, job_logger)
                job = db.get(Job, job.id)
                if job:
                    job.status = JobStatus.COMPLETED.value
                    job.completed_at = datetime.utcnow()
                    write_job_snapshot(self.settings, job)
                    db.commit()
                job_logger.info("Trabajo completado")
            except Exception as exc:
                db.rollback()
                job = db.get(Job, job_id)
                if job and job.status != JobStatus.CANCELLED.value:
                    job.status = JobStatus.FAILED.value
                    job.error_message = str(exc)
                    job.completed_at = datetime.utcnow()
                    write_job_snapshot(self.settings, job)
                    db.commit()
                job_logger.exception("Trabajo fallido: %s", exc)

    async def _plan(self, db: Session, job: Job, job_logger: logging.Logger) -> None:
        if job.scenes:
            return
        job.status = JobStatus.PLANNING.value
        job.started_at = datetime.utcnow()
        db.commit()
        plan = await self.planner.create_plan(
            JobCreate(
                topic=job.topic,
                duration_seconds=job.duration_seconds,
                scene_duration_seconds=job.scene_duration_seconds,
                language=job.language,
                aspect_ratio=job.aspect_ratio,
                width=job.width,
                height=job.height,
                fps=job.fps,
            )
        )
        job.title = plan.title
        job.hook = plan.hook
        job.script_path = str(write_script(self.settings, job.id, plan))
        for planned in plan.scenes:
            db.add(
                Scene(
                    job_id=job.id,
                    scene_number=planned.scene_number,
                    duration_seconds=planned.duration_seconds,
                    visual_prompt=planned.visual_prompt,
                    narration=planned.narration,
                    subtitle=planned.subtitle,
                    status=SceneStatus.PENDING.value,
                )
            )
        db.commit()
        db.expire_all()
        write_job_snapshot(self.settings, job)
        job_logger.info("Plan creado con %s escenas", len(plan.scenes))

    async def _generate_video(self, db: Session, job_id: str, job_logger: logging.Logger) -> None:
        job = db.scalar(select(Job).where(Job.id == job_id).options(selectinload(Job.scenes)).execution_options(populate_existing=True))
        if job is None:
            return
        job.status = JobStatus.GENERATING_VIDEO.value
        db.commit()
        for scene in job.scenes:
            if scene.video_path and scene.status == SceneStatus.COMPLETED.value:
                continue
            if self._is_cancelled(db, job_id):
                return
            scene.status = SceneStatus.GENERATING.value
            db.commit()
            output_path = scene_clip_path(self.settings, job_id, scene.scene_number)
            try:
                result = await self.video_provider.generate_scene_video(
                    visual_prompt=scene.visual_prompt,
                    width=job.width,
                    height=job.height,
                    duration_seconds=scene.duration_seconds,
                    fps=job.fps,
                    output_path=output_path,
                    filename_prefix=f"{job_id}_scene_{scene.scene_number:03d}",
                )
            except Exception as exc:
                scene.status = SceneStatus.FAILED.value
                scene.error_message = str(exc)
                db.commit()
                raise
            scene.video_path = str(result.path)
            scene.prompt_id = result.prompt_id
            scene.seed = result.seed
            scene.generation_seconds = result.generation_seconds
            scene.status = SceneStatus.COMPLETED.value
            db.commit()
            job_logger.info("Escena %03d video generado prompt_id=%s seconds=%.2f", scene.scene_number, scene.prompt_id, scene.generation_seconds)

    async def _generate_audio(self, db: Session, job_id: str, job_logger: logging.Logger) -> None:
        job = db.scalar(select(Job).where(Job.id == job_id).options(selectinload(Job.scenes)).execution_options(populate_existing=True))
        if job is None:
            return
        job.status = JobStatus.GENERATING_AUDIO.value
        db.commit()
        for scene in job.scenes:
            if self._is_cancelled(db, job_id):
                return
            output_path = scene_audio_path(self.settings, job_id, scene.scene_number)
            try:
                result = await self.tts_provider.generate_scene_audio(
                    scene.narration,
                    scene.duration_seconds,
                    output_path,
                    filename_prefix=f"{job_id}_scene_{scene.scene_number:03d}_tts",
                )
            except Exception as exc:
                scene.audio_error = str(exc)
                db.commit()
                raise
            scene.audio_path = str(result.path)
            scene.audio_prompt_id = result.prompt_id
            scene.audio_error = None
            db.commit()
            job_logger.info("Escena %03d audio generado prompt_id=%s seconds=%.2f", scene.scene_number, scene.audio_prompt_id, result.generation_seconds)

    async def _assemble(self, db: Session, job_id: str, job_logger: logging.Logger) -> None:
        job = db.scalar(select(Job).where(Job.id == job_id).options(selectinload(Job.scenes)).execution_options(populate_existing=True))
        if job is None:
            return
        job.status = JobStatus.ASSEMBLING.value
        db.commit()
        subtitles_path = self.settings.jobs_dir / job_id / "subtitles" / "final.srt"
        generate_srt(job.scenes, subtitles_path)
        final_path = self.assembler.assemble(job_id, job.scenes, subtitles_path, width=job.width, height=job.height, fps=job.fps)
        job.final_video_path = str(final_path)
        db.commit()
        job_logger.info("Video final ensamblado en %s", final_path)

    @staticmethod
    def _is_cancelled(db: Session, job_id: str) -> bool:
        status = db.scalar(select(Job.status).where(Job.id == job_id))
        return status == JobStatus.CANCELLED.value
