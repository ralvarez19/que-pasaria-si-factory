from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import JobStatus, SceneStatus
from app.db.session import get_db
from app.models.job import Job, Scene
from app.schemas.jobs import (
    HealthResponse,
    JobCreate,
    JobListResponse,
    JobQueuedResponse,
    JobResponse,
    SceneResponse,
    TelegramSendResponse,
    TTSTestRequest,
    TTSTestResponse,
)
from app.services.paths import write_job_snapshot
from app.services.outputs import latest_video_path
from app.services.worker import JobWorker

router = APIRouter()


def get_worker(request: Request) -> JobWorker:
    return request.app.state.worker


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/api/v1/jobs", response_model=JobQueuedResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(request_body: JobCreate, db: Session = Depends(get_db), worker: JobWorker = Depends(get_worker)) -> JobQueuedResponse:
    job = worker.create_job(db, request_body)
    await worker.enqueue(job.id)
    return JobQueuedResponse(job_id=job.id, status=JobStatus(job.status))


@router.post("/api/v1/tts/test", response_model=TTSTestResponse)
async def test_tts(request_body: TTSTestRequest, worker: JobWorker = Depends(get_worker)) -> TTSTestResponse:
    output_dir = worker.settings.data_dir / "tts_tests"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"tts_test.{worker.settings.tts_audio_format.strip().lstrip('.') or 'wav'}"
    try:
        result = await worker.tts_provider.generate_scene_audio(
            request_body.text,
            worker.settings.scene_duration_seconds,
            output_path,
            filename_prefix="tts_test",
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return TTSTestResponse(audio_path=str(result.path), prompt_id=result.prompt_id)


@router.get("/api/v1/jobs", response_model=JobListResponse)
def list_jobs(db: Session = Depends(get_db)) -> JobListResponse:
    jobs = db.scalars(select(Job).order_by(Job.created_at.desc())).all()
    return JobListResponse(jobs=[JobResponse.model_validate(job) for job in jobs])


@router.get("/api/v1/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobResponse:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job no encontrado")
    return JobResponse.model_validate(job)


@router.get("/api/v1/jobs/{job_id}/scenes", response_model=list[SceneResponse])
def get_job_scenes(job_id: str, db: Session = Depends(get_db)) -> list[SceneResponse]:
    if db.get(Job, job_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job no encontrado")
    scenes = db.scalars(select(Scene).where(Scene.job_id == job_id).order_by(Scene.scene_number)).all()
    return [SceneResponse.model_validate(scene) for scene in scenes]


@router.post("/api/v1/jobs/{job_id}/cancel", response_model=JobResponse)
def cancel_job(job_id: str, db: Session = Depends(get_db), worker: JobWorker = Depends(get_worker)) -> JobResponse:
    job = db.scalar(select(Job).where(Job.id == job_id).options(selectinload(Job.scenes)))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job no encontrado")
    if job.status == JobStatus.COMPLETED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No se puede cancelar un trabajo completado")
    job.status = JobStatus.CANCELLED.value
    for scene in job.scenes:
        if scene.status in {SceneStatus.PENDING.value, SceneStatus.GENERATING.value}:
            scene.status = SceneStatus.SKIPPED.value
    db.commit()
    write_job_snapshot(worker.settings, job)
    return JobResponse.model_validate(job)


@router.post("/api/v1/jobs/{job_id}/retry", response_model=JobQueuedResponse)
async def retry_job(job_id: str, db: Session = Depends(get_db), worker: JobWorker = Depends(get_worker)) -> JobQueuedResponse:
    job = db.scalar(select(Job).where(Job.id == job_id).options(selectinload(Job.scenes)))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job no encontrado")
    if job.status not in {JobStatus.FAILED.value, JobStatus.CANCELLED.value}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Solo se pueden reintentar trabajos fallidos o cancelados")
    job.status = JobStatus.QUEUED.value
    job.error_message = None
    job.completed_at = None
    job.telegram_status = "pending" if worker.settings.telegram_enabled else "disabled"
    job.telegram_error = None
    job.telegram_sent_at = None
    job.telegram_message_id = None
    for scene in job.scenes:
        if scene.status in {SceneStatus.FAILED.value, SceneStatus.SKIPPED.value, SceneStatus.GENERATING.value}:
            scene.status = SceneStatus.PENDING.value
            scene.error_message = None
    db.commit()
    write_job_snapshot(worker.settings, job)
    await worker.enqueue(job.id)
    return JobQueuedResponse(job_id=job.id, status=JobStatus.QUEUED)


@router.get("/api/v1/jobs/{job_id}/download")
def download_job(job_id: str, db: Session = Depends(get_db)) -> FileResponse:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job no encontrado")
    if not job.final_video_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El video final aun no existe")
    final_path = Path(job.final_video_path)
    if not final_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El archivo final no existe en disco")
    return FileResponse(final_path, media_type="video/mp4", filename=f"{job.id}.mp4")


@router.post("/api/v1/jobs/latest/send-telegram", response_model=TelegramSendResponse)
async def send_latest_to_telegram(worker: JobWorker = Depends(get_worker)) -> TelegramSendResponse:
    path = latest_video_path(worker.settings)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"El ultimo video no existe: {path}")
    configuration_error = worker.telegram_notifier.configuration_error()
    if configuration_error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=configuration_error)
    result = await worker.send_latest_telegram("🎬 Último video generado\n\nVideo reenviado desde Qué Pasaría Si Factory.")
    return TelegramSendResponse(
        ok=result.ok,
        status=result.status,
        method=result.method,
        video_path=result.video_path,
        error=result.error,
        telegram_message_id=result.telegram_message_id,
    )


@router.post("/api/v1/jobs/{job_id}/send-telegram", response_model=TelegramSendResponse)
async def send_job_to_telegram(job_id: str, db: Session = Depends(get_db), worker: JobWorker = Depends(get_worker)) -> TelegramSendResponse:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job no encontrado")
    final_path = worker.settings.jobs_dir / job_id / "final" / "final.mp4"
    if not final_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"El archivo final no existe en disco: {final_path}")
    configuration_error = worker.telegram_notifier.configuration_error()
    if configuration_error:
        job.telegram_status = "disabled" if not worker.settings.telegram_enabled else "failed"
        job.telegram_error = configuration_error
        write_job_snapshot(worker.settings, job)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=configuration_error)

    result = await worker.send_telegram_for_job(db, job_id, video_path_override=final_path)
    if not result.ok:
        return TelegramSendResponse(
            ok=False,
            status=result.status,
            method=result.method,
            video_path=result.video_path,
            error=result.error,
            telegram_message_id=result.telegram_message_id,
        )
    return TelegramSendResponse(
        ok=True,
        status=result.status,
        method=result.method,
        video_path=result.video_path,
        error=result.error,
        telegram_message_id=result.telegram_message_id,
    )
