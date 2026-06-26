from pathlib import Path

from app.models.job import Scene
from app.services.subtitles import format_srt_timestamp, generate_srt


def test_format_srt_timestamp() -> None:
    assert format_srt_timestamp(4.5) == "00:00:04,500"


def test_generate_srt_keeps_scene_windows(tmp_path: Path) -> None:
    scenes = [
        Scene(job_id="job", scene_number=1, duration_seconds=4, visual_prompt="prompt one", narration="n1", subtitle="Uno"),
        Scene(job_id="job", scene_number=2, duration_seconds=4, visual_prompt="prompt two", narration="n2", subtitle="Dos"),
    ]
    output = generate_srt(scenes, tmp_path / "final.srt")

    text = output.read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:04,000" in text
    assert "00:00:04,000 --> 00:00:08,000" in text
    assert "Uno" in text
    assert "Dos" in text
