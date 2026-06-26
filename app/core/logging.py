import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    Path(settings.log_file).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            RotatingFileHandler(settings.log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )


def get_job_logger(job_id: str, jobs_dir: Path) -> logging.Logger:
    logger = logging.getLogger(f"job.{job_id}")
    logger.setLevel(logging.INFO)
    log_path = jobs_dir / job_id / "logs" / "job.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if not any(isinstance(handler, RotatingFileHandler) and handler.baseFilename == str(log_path.resolve()) for handler in logger.handlers):
        handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    return logger
