from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.providers.tts import AutoTTSProvider, ComfyUITTSProvider, GeneratedAudioResult, SilentTTSProvider, clean_narration_for_tts, sanitize_tts_text
from app.services.comfyui import ComfyUIClient, ComfyUIError
from app.services.workflow import WorkflowConfigurationError


class FakeComfyTTSClient:
    def __init__(self, history: dict | None = None):
        self.history = history or {"outputs": {"1": {"audio": [{"filename": "voice.wav", "type": "output", "subfolder": ""}]}}}

    async def generate_tts_audio(self, *, text: str, filename_prefix: str, seed: int | None = None):
        return "tts-prompt-id", self.history

    @staticmethod
    def find_generated_audio(history: dict):
        return ComfyUIClient.find_generated_audio(history)

    async def download_output_file(self, output: dict, destination: Path):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"fake wav")
        return destination


class FakeElevenResponse:
    def __init__(self, status_code: int = 200, content: bytes = b"mp3", text: str = ""):
        self.status_code = status_code
        self.content = content
        self.text = text


class FakeElevenClient:
    response = FakeElevenResponse()
    calls: list[dict] = []
    raises: Exception | None = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        if self.raises:
            raise self.raises
        return self.response


@pytest.mark.asyncio
async def test_silent_tts_provider_creates_audio_with_ffmpeg_mock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], capture_output: bool, text: bool, check: bool):
        calls.append(command)
        Path(command[-1]).write_bytes(b"silent")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("app.providers.tts.subprocess.run", fake_run)
    provider = SilentTTSProvider(Settings(ffmpeg_path="ffmpeg"))

    result = await provider.generate_scene_audio("hola", 4, tmp_path / "scene_001.wav")

    assert result.path.exists()
    assert result.prompt_id is None
    assert "-f" in calls[0]


@pytest.mark.asyncio
async def test_comfyui_tts_missing_workflow_fails_clearly(tmp_path: Path) -> None:
    settings = Settings(comfyui_tts_workflow=tmp_path / "missing.json", workflow_bindings_path=tmp_path / "bindings.json")
    provider = ComfyUITTSProvider(settings)

    with pytest.raises(WorkflowConfigurationError, match="Falta el archivo requerido"):
        await provider.generate_scene_audio("hola", 4, tmp_path / "scene_001.wav")


@pytest.mark.asyncio
async def test_comfyui_tts_missing_bindings_fails_clearly(tmp_path: Path) -> None:
    workflow = tmp_path / "tts.json"
    bindings = tmp_path / "bindings.json"
    workflow.write_text('{"1":{"class_type":"Text","inputs":{"text":"hola"}}}', encoding="utf-8")
    bindings.write_text('{"tts":{}}', encoding="utf-8")
    provider = ComfyUITTSProvider(Settings(comfyui_tts_workflow=workflow, workflow_bindings_path=bindings))

    with pytest.raises(WorkflowConfigurationError, match="node_id"):
        await provider.generate_scene_audio("hola", 4, tmp_path / "scene_001.wav")


@pytest.mark.asyncio
async def test_comfyui_tts_success_simulated(tmp_path: Path) -> None:
    provider = ComfyUITTSProvider(Settings())
    provider.client = FakeComfyTTSClient()  # type: ignore[assignment]

    result = await provider.generate_scene_audio("hola", 4, tmp_path / "scene_001.wav", filename_prefix="scene_001")

    assert result.prompt_id == "tts-prompt-id"
    assert result.path.read_bytes() == b"fake wav"


@pytest.mark.asyncio
async def test_comfyui_tts_history_without_audio_fails(tmp_path: Path) -> None:
    provider = ComfyUITTSProvider(Settings())
    provider.client = FakeComfyTTSClient({"outputs": {"1": {"images": [{"filename": "image.png"}]}}})  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="no se encontro audio"):
        await provider.generate_scene_audio("hola", 4, tmp_path / "scene_001.wav")


@pytest.mark.asyncio
async def test_comfyui_submit_workflow_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        status_code = 400
        text = "bad workflow"

        def json(self):
            return {}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("app.services.comfyui.httpx.AsyncClient", FakeAsyncClient)

    with pytest.raises(ComfyUIError, match="HTTP 400 bad workflow"):
        await ComfyUIClient(Settings()).submit_workflow({})


def test_sanitize_tts_text_preserves_spanish_and_replaces_punctuation() -> None:
    text = "¿Qué pasaría si...\nLa Luna desapareciera? El océano cambiaría; mañana: nueva era."

    sanitized = sanitize_tts_text(text)

    assert sanitized == "¿Qué pasaría si, La Luna desapareciera? El océano cambiaría, mañana, nueva era"
    assert "ñ" in sanitized
    assert "é" in sanitized
    assert "\n" not in sanitized
    assert "." not in sanitized


def test_sanitize_tts_text_truncates_long_text() -> None:
    text = " ".join(["Mañana"] * 80)

    sanitized = sanitize_tts_text(text)

    assert len(sanitized) <= 180
    assert "Mañana" in sanitized


def test_clean_narration_for_tts_limits_short_scenes_without_cutting_words() -> None:
    text = "El océano cambiaría durante años. La humanidad tendría nuevas dificultades."

    cleaned = clean_narration_for_tts(text, max_chars=65)

    assert len(cleaned) <= 65
    assert cleaned == "El océano cambiaría durante años, La humanidad tendría nuevas"
    assert "ñ" in cleaned


def test_clean_narration_for_tts_replaces_periods_without_touching_accents() -> None:
    text = "Al principio, el cielo perdería su punto más familiar. La noche parecería extraña."

    cleaned = clean_narration_for_tts(text, max_chars=None)

    assert cleaned == "Al principio, el cielo perdería su punto más familiar, La noche parecería extraña"
    assert "." not in cleaned
    assert "perdería" in cleaned


def test_clean_narration_for_tts_compacts_ellipsis_and_commas() -> None:
    text = "La Luna desaparece...  luego,, todo cambia: lentamente; sin ruido."

    cleaned = clean_narration_for_tts(text, max_chars=None)

    assert cleaned == "La Luna desaparece, luego, todo cambia, lentamente, sin ruido"


@pytest.mark.asyncio
async def test_auto_tts_without_api_key_uses_comfyui(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    async def fake_comfy(self, text, duration_seconds, output_path, filename_prefix=None):
        output_path.write_bytes(b"audio")
        return GeneratedAudioResult(output_path, "comfy", provider_used="comfyui")

    monkeypatch.setattr("app.providers.tts.ComfyUITTSProvider.generate_scene_audio", fake_comfy)
    provider = AutoTTSProvider(Settings(tts_provider="auto", elevenlabs_enabled=True, elevenlabs_api_key="", elevenlabs_voice_id="voice"))

    result = await provider.generate_scene_audio("hola", 4, tmp_path / "scene.wav")

    assert result.provider_used == "comfyui"


@pytest.mark.asyncio
async def test_auto_tts_with_api_key_uses_elevenlabs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    FakeElevenClient.response = FakeElevenResponse(200, b"mp3")
    FakeElevenClient.calls = []
    FakeElevenClient.raises = None
    monkeypatch.setattr("app.services.tts.elevenlabs_tts_provider.httpx.AsyncClient", FakeElevenClient)
    provider = AutoTTSProvider(
        Settings(tts_provider="auto", elevenlabs_enabled=True, elevenlabs_api_key="secret-key", elevenlabs_voice_id="voice")
    )

    result = await provider.generate_scene_audio("hola", 4, tmp_path / "scene.wav")

    assert result.provider_used == "elevenlabs"
    assert result.path.suffix == ".mp3"
    assert FakeElevenClient.calls
    assert "secret-key" in FakeElevenClient.calls[0]["kwargs"]["headers"]["xi-api-key"]


@pytest.mark.asyncio
async def test_elevenlabs_401_falls_back_to_comfyui(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    await assert_elevenlabs_error_falls_back(monkeypatch, tmp_path, FakeElevenResponse(401, b"", "unauthorized"))


@pytest.mark.asyncio
async def test_elevenlabs_429_falls_back_to_comfyui(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    await assert_elevenlabs_error_falls_back(monkeypatch, tmp_path, FakeElevenResponse(429, b"", "quota"))


@pytest.mark.asyncio
async def test_elevenlabs_timeout_falls_back_to_comfyui(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import httpx

    FakeElevenClient.response = FakeElevenResponse()
    FakeElevenClient.calls = []
    FakeElevenClient.raises = httpx.TimeoutException("timeout")
    monkeypatch.setattr("app.services.tts.elevenlabs_tts_provider.httpx.AsyncClient", FakeElevenClient)

    async def fake_comfy(self, text, duration_seconds, output_path, filename_prefix=None):
        output_path.write_bytes(b"audio")
        return GeneratedAudioResult(output_path, "comfy", provider_used="comfyui")

    monkeypatch.setattr("app.providers.tts.ComfyUITTSProvider.generate_scene_audio", fake_comfy)
    provider = AutoTTSProvider(Settings(tts_provider="auto", elevenlabs_enabled=True, elevenlabs_api_key="secret-key", elevenlabs_voice_id="voice"))

    result = await provider.generate_scene_audio("hola", 4, tmp_path / "scene.wav")

    assert result.provider_used == "comfyui"
    assert result.fallback_used is True
    assert "secret-key" not in (result.error or "")


@pytest.mark.asyncio
async def test_elevenlabs_without_token_fails_when_fallback_disabled(tmp_path: Path) -> None:
    provider = AutoTTSProvider(Settings(tts_provider="elevenlabs", elevenlabs_enabled=True, elevenlabs_api_key="", elevenlabs_voice_id="voice", elevenlabs_fallback_to_comfyui=False))

    with pytest.raises(Exception, match="ELEVENLABS_API_KEY"):
        await provider.generate_scene_audio("hola", 4, tmp_path / "scene.wav")


async def assert_elevenlabs_error_falls_back(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, response: FakeElevenResponse) -> None:
    FakeElevenClient.response = response
    FakeElevenClient.calls = []
    FakeElevenClient.raises = None
    monkeypatch.setattr("app.services.tts.elevenlabs_tts_provider.httpx.AsyncClient", FakeElevenClient)

    async def fake_comfy(self, text, duration_seconds, output_path, filename_prefix=None):
        output_path.write_bytes(b"audio")
        return GeneratedAudioResult(output_path, "comfy", provider_used="comfyui")

    monkeypatch.setattr("app.providers.tts.ComfyUITTSProvider.generate_scene_audio", fake_comfy)
    provider = AutoTTSProvider(Settings(tts_provider="auto", elevenlabs_enabled=True, elevenlabs_api_key="secret-key", elevenlabs_voice_id="voice"))

    result = await provider.generate_scene_audio("hola", 4, tmp_path / "scene.wav")

    assert result.provider_used == "comfyui"
    assert result.fallback_used is True
    assert "secret-key" not in (result.error or "")
