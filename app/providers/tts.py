import subprocess
import random
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import Settings
from app.services.comfyui import ComfyUIClient


class GeneratedAudioResult:
    def __init__(self, path: Path, prompt_id: str | None, generation_seconds: float = 0.0):
        self.path = path
        self.prompt_id = prompt_id
        self.generation_seconds = generation_seconds


class TTSProvider(ABC):
    @abstractmethod
    async def generate_scene_audio(self, text: str, duration_seconds: int, output_path: Path, filename_prefix: str | None = None) -> GeneratedAudioResult:
        raise NotImplementedError


class SilentTTSProvider(TTSProvider):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def generate_scene_audio(self, text: str, duration_seconds: int, output_path: Path, filename_prefix: str | None = None) -> GeneratedAudioResult:
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
        return GeneratedAudioResult(output_path, None, 0.0)


class ComfyUITTSProvider(TTSProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = ComfyUIClient(settings)

    async def generate_scene_audio(self, text: str, duration_seconds: int, output_path: Path, filename_prefix: str | None = None) -> GeneratedAudioResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        start = time.monotonic()
        prefix = filename_prefix or output_path.with_suffix("").name
        prompt_id, history = await self.client.generate_tts_audio(
            text=sanitize_tts_text(text),
            filename_prefix=prefix,
            seed=random.randint(1, 2_147_483_647),
        )
        generated = self.client.find_generated_audio(history)
        if generated is None:
            raise RuntimeError(f"ComfyUI TTS termino el prompt {prompt_id}, pero no se encontro audio en /history.")
        await self.client.download_output_file(generated, output_path)
        return GeneratedAudioResult(output_path, prompt_id, time.monotonic() - start)


def get_tts_provider(settings: Settings) -> TTSProvider:
    if settings.tts_provider.lower() == "comfyui":
        return ComfyUITTSProvider(settings)
    return SilentTTSProvider(settings)


def sanitize_tts_text(text: str, max_chars: int = 180) -> str:
    cleaned = text.replace("\r", " ").replace("\n", " ")
    cleaned = cleaned.replace("...", ",")
    cleaned = cleaned.replace(".", ",")
    cleaned = cleaned.replace(";", ",").replace(":", ",")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    truncated = cleaned[:max_chars].rstrip()
    last_break = max(truncated.rfind(","), truncated.rfind(" "))
    if last_break >= 80:
        truncated = truncated[:last_break].rstrip(" ,")
    return truncated
