from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import init_db
from app.providers.planner import get_planner_provider
from app.providers.tts import get_tts_provider
from app.providers.video import get_video_provider
from app.services.ffmpeg import FFmpegAssembler
from app.services.worker import JobWorker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    settings.jobs_dir.mkdir(parents=True, exist_ok=True)
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)
    configure_logging(settings)
    init_db()
    worker = JobWorker(
        settings=settings,
        planner=get_planner_provider(settings),
        video_provider=get_video_provider(settings),
        tts_provider=get_tts_provider(settings),
        assembler=FFmpegAssembler(settings),
    )
    app.state.worker = worker
    await worker.start()
    try:
        yield
    finally:
        await worker.stop()


app = FastAPI(title="Qué pasaría si - Content Factory", lifespan=lifespan)
app.include_router(router)
