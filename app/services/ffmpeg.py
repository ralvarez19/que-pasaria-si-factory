import shutil
import subprocess
from pathlib import Path

from app.core.config import Settings
from app.models.job import Scene


class FFmpegError(RuntimeError):
    pass


class FFmpegAssembler:
    def __init__(self, settings: Settings):
        self.settings = settings

    def validate(self) -> None:
        if shutil.which(self.settings.ffmpeg_path) is None and not Path(self.settings.ffmpeg_path).exists():
            raise FFmpegError(f"FFmpeg no esta disponible en '{self.settings.ffmpeg_path}'.")

    def assemble(self, job_id: str, scenes: list[Scene], subtitles_path: Path, *, width: int, height: int, fps: int) -> Path:
        self.validate()
        job_root = self.settings.jobs_dir / job_id
        temp_dir = job_root / "temp"
        final_dir = job_root / "final"
        temp_dir.mkdir(parents=True, exist_ok=True)
        final_dir.mkdir(parents=True, exist_ok=True)

        normalized_clips = self._normalize_clips(scenes, temp_dir, width=width, height=height, fps=fps)
        concat_list = temp_dir / "ffmpeg_concat_list.txt"
        concat_list.write_text(
            "".join(f"file '{clip.resolve().as_posix()}'\n" for clip in normalized_clips),
            encoding="utf-8",
        )
        joined_video = temp_dir / "joined.mp4"
        self._run([
            self.settings.ffmpeg_path,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c",
            "copy",
            str(joined_video),
        ])

        audio_list = temp_dir / "ffmpeg_audio_list.txt"
        audio_paths = [Path(scene.audio_path) for scene in sorted(scenes, key=lambda item: item.scene_number) if scene.audio_path]
        audio_list.write_text("".join(f"file '{path.resolve().as_posix()}'\n" for path in audio_paths), encoding="utf-8")
        joined_audio = temp_dir / "joined_audio.m4a"
        self._run([
            self.settings.ffmpeg_path,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(audio_list),
            "-c",
            "copy",
            str(joined_audio),
        ])

        final_path = final_dir / "final.mp4"
        subtitle_filter = f"subtitles='{self._filter_path(subtitles_path)}'"
        self._run([
            self.settings.ffmpeg_path,
            "-y",
            "-i",
            str(joined_video),
            "-i",
            str(joined_audio),
            "-vf",
            subtitle_filter,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(final_path),
        ])
        return final_path

    def _normalize_clips(self, scenes: list[Scene], temp_dir: Path, *, width: int, height: int, fps: int) -> list[Path]:
        normalized: list[Path] = []
        for scene in sorted(scenes, key=lambda item: item.scene_number):
            if not scene.video_path:
                raise FFmpegError(f"La escena {scene.scene_number} no tiene video_path.")
            input_path = Path(scene.video_path)
            if not input_path.exists():
                raise FFmpegError(f"No existe el clip de la escena {scene.scene_number}: {input_path}")
            output_path = temp_dir / f"normalized_scene_{scene.scene_number:03d}.mp4"
            self._run([
                self.settings.ffmpeg_path,
                "-y",
                "-i",
                str(input_path),
                "-vf",
                f"scale={width}:{height},fps={fps}",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-an",
                str(output_path),
            ])
            normalized.append(output_path)
        return normalized

    @staticmethod
    def _run(command: list[str]) -> None:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise FFmpegError(f"Comando FFmpeg fallo: {' '.join(command)}\n{completed.stderr.strip()}")

    @staticmethod
    def _filter_path(path: Path) -> str:
        return path.resolve().as_posix().replace(":", "\\:").replace("'", "\\'")
