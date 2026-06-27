from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.models.job import Scene
from app.services.ffmpeg import FFmpegAssembler, FFmpegError


def test_ffmpeg_validate_raises_for_missing_binary(tmp_path: Path) -> None:
    settings = Settings(ffmpeg_path=str(tmp_path / "missing-ffmpeg"))
    assembler = FFmpegAssembler(settings)

    with pytest.raises(FFmpegError):
        assembler.validate()


def test_ffmpeg_assemble_invokes_commands_with_mock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = Settings(ffmpeg_path="ffmpeg", jobs_dir=tmp_path)
    assembler = FFmpegAssembler(settings)
    clip = tmp_path / "clip.mp4"
    audio = tmp_path / "audio.m4a"
    subtitles = tmp_path / "job" / "subtitles" / "final.srt"
    clip.write_bytes(b"clip")
    audio.write_bytes(b"audio")
    subtitles.parent.mkdir(parents=True)
    subtitles.write_text("1\n00:00:00,000 --> 00:00:01,000\nHola\n", encoding="utf-8")
    calls: list[list[str]] = []

    monkeypatch.setattr("app.services.ffmpeg.shutil.which", lambda _: "ffmpeg")

    def fake_run(command: list[str], capture_output: bool, text: bool, check: bool) -> SimpleNamespace:
        calls.append(command)
        output = Path(command[-1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"out")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("app.services.ffmpeg.subprocess.run", fake_run)
    scenes = [Scene(job_id="job", scene_number=1, duration_seconds=4, visual_prompt="prompt", narration="n", subtitle="s", video_path=str(clip), audio_path=str(audio))]

    final = assembler.assemble("job", scenes, subtitles, width=1280, height=720, fps=25)

    assert final.name == "final.mp4"
    assert len(calls) == 5
    assert any("apad,atrim=0:4" in part for call in calls for part in call)
