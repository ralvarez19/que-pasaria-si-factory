from pathlib import Path

from app.models.job import Scene


def format_srt_timestamp(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def generate_srt(scenes: list[Scene], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    elapsed = 0.0
    for index, scene in enumerate(sorted(scenes, key=lambda item: item.scene_number), start=1):
        start = elapsed
        end = elapsed + scene.duration_seconds
        lines.extend(
            [
                str(index),
                f"{format_srt_timestamp(start)} --> {format_srt_timestamp(end)}",
                scene.subtitle,
                "",
            ]
        )
        elapsed = end
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
