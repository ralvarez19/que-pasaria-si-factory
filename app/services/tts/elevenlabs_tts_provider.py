import logging
import time
from pathlib import Path

import httpx

from app.core.config import Settings
from app.providers.tts import GeneratedAudioResult

logger = logging.getLogger(__name__)


class ElevenLabsTTSError(RuntimeError):
    pass


class ElevenLabsTTSProvider:
    provider_name = "elevenlabs"

    def __init__(self, settings: Settings):
        self.settings = settings

    def is_configured(self) -> bool:
        return bool(self.settings.elevenlabs_enabled and self.settings.elevenlabs_api_key.strip() and self.settings.elevenlabs_voice_id.strip())

    def configuration_error(self) -> str | None:
        if not self.settings.elevenlabs_enabled:
            return "ElevenLabs deshabilitado"
        if not self.settings.elevenlabs_api_key.strip():
            return "Falta ELEVENLABS_API_KEY"
        if not self.settings.elevenlabs_voice_id.strip():
            return "Falta ELEVENLABS_VOICE_ID"
        return None

    async def generate_scene_audio(self, text: str, duration_seconds: int, output_path: Path, filename_prefix: str | None = None) -> GeneratedAudioResult:
        error = self.configuration_error()
        if error:
            raise ElevenLabsTTSError(error)

        extension = self._extension_from_output_format()
        if output_path.suffix.lower() == f".{extension}":
            target = output_path
            target.parent.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = output_path.parent / "elevenlabs"
            output_dir.mkdir(parents=True, exist_ok=True)
            target = output_dir / f"{output_path.stem}.{extension}"
        start = time.monotonic()

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.settings.elevenlabs_voice_id.strip()}"
        params = {"output_format": self.settings.elevenlabs_output_format}
        payload = {
            "text": text,
            "model_id": self.settings.elevenlabs_model_id,
            "voice_settings": {
                "stability": self.settings.elevenlabs_stability,
                "similarity_boost": self.settings.elevenlabs_similarity_boost,
                "style": self.settings.elevenlabs_style,
                "use_speaker_boost": self.settings.elevenlabs_use_speaker_boost,
            },
        }
        headers = {
            "xi-api-key": self.settings.elevenlabs_api_key.strip(),
            "accept": "audio/mpeg",
            "content-type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.settings.elevenlabs_timeout_seconds) as client:
                response = await client.post(url, params=params, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise ElevenLabsTTSError("ElevenLabs timeout") from exc
        except httpx.HTTPError as exc:
            raise ElevenLabsTTSError(f"ElevenLabs HTTP error: {exc}") from exc

        if response.status_code >= 400:
            detail = response.text[:500]
            if response.status_code in {401, 403}:
                raise ElevenLabsTTSError(f"ElevenLabs autenticacion fallida HTTP {response.status_code}: {detail}")
            if response.status_code == 429:
                raise ElevenLabsTTSError(f"ElevenLabs limite o cuota agotada HTTP 429: {detail}")
            raise ElevenLabsTTSError(f"ElevenLabs rechazo la solicitud HTTP {response.status_code}: {detail}")

        target.write_bytes(response.content)
        if target.stat().st_size <= 0:
            raise ElevenLabsTTSError("ElevenLabs devolvio audio vacio")
        logger.info("ElevenLabs audio generado path=%s size=%s", target, target.stat().st_size)
        return GeneratedAudioResult(
            target,
            None,
            time.monotonic() - start,
            provider_used="elevenlabs",
            fallback_used=False,
            raw_audio_path=str(target),
        )

    def _extension_from_output_format(self) -> str:
        output_format = self.settings.elevenlabs_output_format.lower()
        if output_format.startswith("mp3"):
            return "mp3"
        if output_format.startswith("pcm"):
            return "pcm"
        if output_format.startswith("ulaw"):
            return "ulaw"
        return "mp3"
