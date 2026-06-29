import subprocess
import random
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import Settings
from app.services.comfyui import ComfyUIClient


class GeneratedAudioResult:
    def __init__(
        self,
        path: Path,
        prompt_id: str | None,
        generation_seconds: float = 0.0,
        *,
        provider_used: str | None = None,
        fallback_used: bool = False,
        raw_audio_path: str | None = None,
        raw_audio_duration_seconds: float | None = None,
        error: str | None = None,
    ):
        self.path = path
        self.prompt_id = prompt_id
        self.generation_seconds = generation_seconds
        self.provider_used = provider_used
        self.fallback_used = fallback_used
        self.raw_audio_path = raw_audio_path or str(path)
        self.raw_audio_duration_seconds = raw_audio_duration_seconds
        self.error = error


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
        return GeneratedAudioResult(output_path, None, 0.0, provider_used="silent", raw_audio_path=str(output_path), raw_audio_duration_seconds=float(duration_seconds))


class ComfyUITTSProvider(TTSProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = ComfyUIClient(settings)

    async def generate_scene_audio(self, text: str, duration_seconds: int, output_path: Path, filename_prefix: str | None = None) -> GeneratedAudioResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        start = time.monotonic()
        prefix = filename_prefix or output_path.with_suffix("").name
        max_chars = 110 if duration_seconds <= 4 else 180
        prompt_id, history = await self.client.generate_tts_audio(
            text=clean_narration_for_tts(text, max_chars=max_chars),
            filename_prefix=prefix,
            seed=random.randint(1, 2_147_483_647),
        )
        generated = self.client.find_generated_audio(history)
        if generated is None:
            raise RuntimeError(f"ComfyUI TTS termino el prompt {prompt_id}, pero no se encontro audio en /history.")
        await self.client.download_output_file(generated, output_path)
        return GeneratedAudioResult(
            output_path,
            prompt_id,
            time.monotonic() - start,
            provider_used="comfyui",
            raw_audio_path=str(output_path),
            raw_audio_duration_seconds=probe_audio_duration(output_path),
        )


class AutoTTSProvider(TTSProvider):
    def __init__(self, settings: Settings, *, forced_provider: str | None = None):
        self.settings = settings
        self.forced_provider = (forced_provider or settings.tts_provider).lower()
        self.comfyui_provider = ComfyUITTSProvider(settings)
        self.silent_provider = SilentTTSProvider(settings)
        from app.services.tts import ElevenLabsTTSProvider

        self.elevenlabs_provider = ElevenLabsTTSProvider(settings)

    async def generate_scene_audio(self, text: str, duration_seconds: int, output_path: Path, filename_prefix: str | None = None) -> GeneratedAudioResult:
        provider = self.forced_provider
        if provider == "silent":
            return await self.silent_provider.generate_scene_audio(text, duration_seconds, output_path, filename_prefix)
        if provider == "comfyui":
            return await self.comfyui_provider.generate_scene_audio(text, duration_seconds, output_path, filename_prefix)
        if provider == "elevenlabs":
            return await self._try_elevenlabs(text, duration_seconds, output_path, filename_prefix, allow_fallback=self.settings.elevenlabs_fallback_to_comfyui)
        if provider == "auto":
            if self.elevenlabs_provider.is_configured():
                return await self._try_elevenlabs(text, duration_seconds, output_path, filename_prefix, allow_fallback=True)
            return await self._fallback_to_comfyui(text, duration_seconds, output_path, filename_prefix, None)
        raise RuntimeError(f"TTS_PROVIDER no soportado: {provider}")

    async def _try_elevenlabs(
        self,
        text: str,
        duration_seconds: int,
        output_path: Path,
        filename_prefix: str | None,
        *,
        allow_fallback: bool,
    ) -> GeneratedAudioResult:
        try:
            return await self.elevenlabs_provider.generate_scene_audio(text, duration_seconds, output_path, filename_prefix)
        except Exception as exc:
            if allow_fallback:
                return await self._fallback_to_comfyui(text, duration_seconds, output_path, filename_prefix, exc)
            raise

    async def _fallback_to_comfyui(
        self,
        text: str,
        duration_seconds: int,
        output_path: Path,
        filename_prefix: str | None,
        error: Exception | None,
    ) -> GeneratedAudioResult:
        result = await self.comfyui_provider.generate_scene_audio(text, duration_seconds, output_path, filename_prefix)
        result.fallback_used = error is not None
        result.error = str(error) if error else None
        return result


def get_tts_provider(settings: Settings) -> TTSProvider:
    provider = settings.tts_provider.lower()
    if provider in {"auto", "elevenlabs"}:
        return AutoTTSProvider(settings)
    if provider == "comfyui":
        return ComfyUITTSProvider(settings)
    return SilentTTSProvider(settings)


def get_tts_provider_for_name(settings: Settings, provider: str) -> TTSProvider:
    provider = provider.lower()
    if provider in {"auto", "elevenlabs"}:
        return AutoTTSProvider(settings, forced_provider=provider)
    if provider == "comfyui":
        return ComfyUITTSProvider(settings)
    if provider == "silent":
        return SilentTTSProvider(settings)
    raise RuntimeError(f"Provider TTS no soportado: {provider}")


def clean_narration_for_tts(text: str, max_chars: int | None = None) -> str:
    cleaned = text.replace("\r", " ").replace("\n", " ")
    cleaned = cleaned.replace("...", ",")
    cleaned = cleaned.replace(";", ",").replace(":", ",")
    cleaned = re.sub(r"(?<!\.)\.(?!\.)", ",", cleaned)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    cleaned = re.sub(r",\s*,+", ", ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,")
    if not cleaned:
        raise ValueError("El texto TTS quedo vacio despues de limpiar")
    if max_chars is None or len(cleaned) <= max_chars:
        return cleaned
    truncated = cleaned[:max_chars].rstrip()
    last_break = max(truncated.rfind(","), truncated.rfind(" "))
    if last_break >= 20:
        truncated = truncated[:last_break].rstrip(" ,")
    if not truncated:
        raise ValueError("El texto TTS quedo vacio despues de recortar")
    return truncated


def sanitize_tts_text(text: str, max_chars: int = 180) -> str:
    return clean_narration_for_tts(text, max_chars=max_chars)


def probe_audio_duration(path: Path) -> float | None:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return None
    try:
        return float(completed.stdout.strip())
    except ValueError:
        return None
