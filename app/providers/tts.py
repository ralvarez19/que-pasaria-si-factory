import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import Settings


class TTSProvider(ABC):
    @abstractmethod
    async def generate_scene_audio(self, text: str, duration_seconds: int, output_path: Path) -> Path:
        raise NotImplementedError


class SilentTTSProvider(TTSProvider):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def generate_scene_audio(self, text: str, duration_seconds: int, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            self.settings.ffmpeg_path,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t",
            str(duration_seconds),
            "-c:a",
            "aac",
            str(output_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"FFmpeg no pudo crear audio silencioso: {completed.stderr.strip()}")
        return output_path


class ComfyUITTSProvider(TTSProvider):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def generate_scene_audio(self, text: str, duration_seconds: int, output_path: Path) -> Path:
        raise NotImplementedError(
            "ComfyUITTSProvider esta preparado como interfaz, pero requiere workflows/audio/chatterbox_tts_api.json "
            "y bindings TTS completos para activarse."
        )


def get_tts_provider(settings: Settings) -> TTSProvider:
    if settings.tts_provider.lower() == "comfyui":
        return ComfyUITTSProvider(settings)
    return SilentTTSProvider(settings)
