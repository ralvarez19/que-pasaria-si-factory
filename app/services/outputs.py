import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.core.config import Settings


@dataclass(slots=True)
class OutputCopies:
    latest_path: Path
    archive_path: Path


def copy_final_outputs(settings: Settings, final_video_path: Path, *, topic: str, job_id: str, created_at: datetime | None = None) -> OutputCopies:
    source = Path(final_video_path).resolve()
    if not source.exists():
        raise FileNotFoundError(f"No existe el video final: {source}")
    if source.stat().st_size <= 0:
        raise ValueError(f"El video final esta vacio: {source}")

    latest_dir = settings.data_dir / "outputs" / "latest"
    archive_dir = settings.data_dir / "outputs" / "archive"
    latest_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)

    latest_path = latest_dir / "final.mp4"
    timestamp = (created_at or datetime.utcnow()).strftime("%Y%m%d_%H%M%S")
    archive_path = archive_dir / f"{timestamp}_{slugify_topic(topic)}_{job_id[:8]}.mp4"

    shutil.copy2(source, latest_path)
    shutil.copy2(source, archive_path)
    return OutputCopies(latest_path=latest_path, archive_path=archive_path)


def latest_video_path(settings: Settings) -> Path:
    return settings.data_dir / "outputs" / "latest" / "final.mp4"


def slugify_topic(topic: str) -> str:
    text = topic.casefold()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
        "¿": "",
        "?": "",
    }
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)
    text = re.sub(r"\bque pasaria si\b", "", text)
    text = re.sub(r"\b(el|la|los|las|un|una|unos|unas)\b", "", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:80] or "video"
