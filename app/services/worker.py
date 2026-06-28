import asyncio
import logging
from datetime import datetime
from pathlib import Path
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
from app.services.outputs import copy_final_outputs, latest_video_path
from app.services.paths import ensure_job_dirs, scene_audio_path, scene_clip_path, write_input_script_copy, write_job_snapshot, write_script
from app.services.script_quality import PROHIBITED_PHRASE, load_manual_script, normalize_manual_narration, resolve_manual_script_path, validate_and_repair_plan
from app.services.subtitles import generate_srt
from app.services.telegram import TelegramNotifier, TelegramSendResult

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
        telegram_notifier: TelegramNotifier,
    ):
        self.settings = settings
        self.planner = planner
        self.video_provider = video_provider
        self.tts_provider = tts_provider
        self.assembler = assembler
        self.telegram_notifier = telegram_notifier
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
        if request.script_path and not Path(request.script_path).exists():
            raise ValueError(f"No existe el guion manual: {request.script_path}")
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
            script_path=request.script_path,
            telegram_status="pending" if self.settings.telegram_enabled else "disabled",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        ensure_job_dirs(self.settings, job.id)
        write_job_snapshot(self.settings, job)
        return job

    def create_job_from_script(self, db: Session, script_path: Path) -> Job:
        manual = load_manual_script(script_path)
        job = Job(
            id=str(uuid4()),
            topic=manual.topic,
            title=manual.title,
            status=JobStatus.QUEUED.value,
            language=manual.language,
            aspect_ratio=manual.aspect_ratio,
            duration_seconds=manual.duration_seconds,
            scene_duration_seconds=manual.scene_duration_seconds,
            scene_count=len(manual.plan.scenes),
            width=manual.width,
            height=manual.height,
            fps=manual.fps,
            script_path=str(script_path),
            telegram_status="pending" if self.settings.telegram_enabled else "disabled",
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
                await self.send_telegram_for_job(db, job_id, job_logger)
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
        request = JobCreate(
            topic=job.topic,
            duration_seconds=job.duration_seconds,
            scene_duration_seconds=job.scene_duration_seconds,
            language=job.language,
            aspect_ratio=job.aspect_ratio,
            width=job.width,
            height=job.height,
            fps=job.fps,
            script_path=job.script_path,
        )
        manual_script_path = resolve_manual_script_path(request)
        if manual_script_path:
            if not manual_script_path.exists():
                if request.script_path:
                    raise ValueError(f"No existe el guion manual: {manual_script_path}")
                manual_script_path = None
        if manual_script_path:
            manual = load_manual_script(manual_script_path)
            plan = manual.plan
            job.topic = manual.topic
            job.title = manual.title
            job.language = manual.language
            job.aspect_ratio = manual.aspect_ratio
            job.duration_seconds = manual.duration_seconds
            job.scene_duration_seconds = manual.scene_duration_seconds
            job.scene_count = len(manual.plan.scenes)
            job.width = manual.width
            job.height = manual.height
            job.fps = manual.fps
            write_input_script_copy(self.settings, job.id, manual_script_path)
            job_logger.info("Guion manual cargado desde %s", manual_script_path)
        else:
            plan = await self.planner.create_plan(request)
            plan = validate_and_repair_plan(plan, request)
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
                    tts_text=planned.tts_text or planned.narration,
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
        self._validate_persisted_script(db, job)
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

    def _validate_persisted_script(self, db: Session, job: Job) -> None:
        if not job.scenes:
            raise ValueError("El job no tiene escenas para generar")
        if not job.title:
            raise ValueError("El job no tiene title")
        for scene in job.scenes:
            if not scene.visual_prompt.strip():
                raise ValueError(f"La escena {scene.scene_number} no tiene visual_prompt")
            if not scene.narration.strip():
                raise ValueError(f"La escena {scene.scene_number} no tiene narration")
            if not scene.subtitle.strip():
                raise ValueError(f"La escena {scene.scene_number} no tiene subtitle")
            if PROHIBITED_PHRASE.casefold() in scene.narration.casefold():
                raise ValueError(f"La escena {scene.scene_number} contiene una frase prohibida")
            scene.tts_text = normalize_manual_narration(scene.tts_text or scene.narration)
        write_job_snapshot(self.settings, job)
        db.commit()

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
                tts_text = scene.tts_text or scene.narration
                job_logger.info("Escena %03d TTS original=%r limpio=%r", scene.scene_number, scene.narration[:120], tts_text[:120])
                result = await self.tts_provider.generate_scene_audio(
                    tts_text,
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
        copies = copy_final_outputs(self.settings, final_path, topic=job.topic, job_id=job.id)
        job.latest_video_path = str(copies.latest_path)
        job.archive_video_path = str(copies.archive_path)
        db.commit()
        job_logger.info("Video final ensamblado en %s", final_path)
        job_logger.info("Video copiado a latest=%s archive=%s", copies.latest_path, copies.archive_path)

    async def send_telegram_for_job(self, db: Session, job_id: str, job_logger: logging.Logger | None = None, video_path_override: Path | None = None) -> TelegramSendResult:
        job_logger = job_logger or get_job_logger(job_id, self.settings.jobs_dir)
        job = db.get(Job, job_id)
        if job is None:
            return TelegramSendResult(ok=False, status="failed", error="Job no encontrado")

        if not self.settings.telegram_enabled:
            job.telegram_status = "disabled"
            job.telegram_error = None
            job.telegram_sent_at = None
            write_job_snapshot(self.settings, job)
            db.commit()
            job_logger.info("Telegram deshabilitado para este job")
            logger.info("Telegram deshabilitado para job %s", job_id)
            return TelegramSendResult(ok=False, status="disabled", video_path=job.final_video_path, error="Telegram deshabilitado")

        if not job.final_video_path and video_path_override is None:
            error = "El job no tiene final_video_path"
            job.telegram_status = "failed"
            job.telegram_error = error
            job.telegram_message_id = None
            write_job_snapshot(self.settings, job)
            db.commit()
            job_logger.error("Telegram no enviado: %s", error)
            return TelegramSendResult(ok=False, status="failed", error=error)

        final_path = Path(video_path_override or job.final_video_path)
        validation_error = self._validate_video_for_telegram(final_path)
        if validation_error:
            job.telegram_status = "failed"
            job.telegram_error = validation_error
            job.telegram_message_id = None
            write_job_snapshot(self.settings, job)
            db.commit()
            job_logger.error("Telegram no enviado: %s", validation_error)
            logger.error("Telegram no enviado para job %s: %s", job_id, validation_error)
            return TelegramSendResult(ok=False, status="failed", video_path=str(final_path), error=validation_error)

        job.telegram_status = "pending"
        job.telegram_error = None
        write_job_snapshot(self.settings, job)
        db.commit()

        final_path = final_path.resolve()
        size_bytes = final_path.stat().st_size
        job_logger.info(
            "Telegram habilitado video=%s size_bytes=%s chat_id=%s",
            final_path,
            size_bytes,
            self.telegram_notifier.masked_chat_id(),
        )
        result = await self._send_telegram_with_retry(final_path, self._telegram_caption(job), job_logger)
        job = db.get(Job, job_id)
        if job is None:
            return result
        job.status = JobStatus.COMPLETED.value
        if result.ok:
            job.telegram_status = "sent"
            job.telegram_error = None
            job.telegram_sent_at = datetime.utcnow()
            job.telegram_message_id = result.telegram_message_id
            job_logger.info("Telegram enviado method=%s message_id=%s", result.method, result.telegram_message_id)
        else:
            job.telegram_status = "failed"
            job.telegram_error = result.error
            job.telegram_sent_at = None
            job.telegram_message_id = None
            job_logger.error("Telegram fallo status=%s error=%s", result.status, result.error)
            logger.error("Telegram fallo para job %s status=%s error=%s", job_id, result.status, result.error)
        write_job_snapshot(self.settings, job)
        db.commit()
        return result

    async def send_latest_telegram(self, caption: str) -> TelegramSendResult:
        path = latest_video_path(self.settings)
        validation_error = self._validate_video_for_telegram(path)
        if validation_error:
            return TelegramSendResult(ok=False, status="failed", video_path=str(path), error=validation_error)
        return await self.telegram_notifier.send_video(path.resolve(), caption)

    async def _send_telegram_with_retry(self, video_path: Path, caption: str, job_logger: logging.Logger) -> TelegramSendResult:
        waits = (2, 5)
        last_result: TelegramSendResult | None = None
        for attempt, wait_seconds in enumerate(waits, start=1):
            job_logger.info("Telegram intento %s: esperando %s segundos antes de enviar", attempt, wait_seconds)
            await asyncio.sleep(wait_seconds)
            validation_error = self._validate_video_for_telegram(video_path)
            if validation_error:
                last_result = TelegramSendResult(ok=False, status="failed", video_path=str(video_path), error=validation_error)
                job_logger.error("Telegram intento %s cancelado: %s", attempt, validation_error)
                continue
            last_result = await self.telegram_notifier.send_video(video_path.resolve(), caption)
            if last_result.ok:
                return last_result
            job_logger.error("Telegram intento %s fallo: %s", attempt, last_result.error)
        return last_result or TelegramSendResult(ok=False, status="failed", video_path=str(video_path), error="Telegram no pudo enviar el video")

    @staticmethod
    def _validate_video_for_telegram(video_path: Path) -> str | None:
        resolved = Path(video_path).resolve()
        if not resolved.exists():
            return f"El video final no existe en disco: {resolved}"
        if resolved.stat().st_size <= 0:
            return f"El video final esta vacio: {resolved}"
        try:
            with resolved.open("rb") as handle:
                handle.read(1)
        except OSError as exc:
            return f"El video final no se puede leer o esta bloqueado: {resolved}: {exc}"
        return None

    @staticmethod
    def _telegram_caption(job: Job) -> str:
        title = job.title or job.topic
        return f"🎬 {title}\n\nVideo generado automáticamente por Qué Pasaría Si Factory.\nJob: {job.id}"

    @staticmethod
    def _is_cancelled(db: Session, job_id: str) -> bool:
        status = db.scalar(select(Job.status).where(Job.id == job_id))
        return status == JobStatus.CANCELLED.value
