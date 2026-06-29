from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Que Pasaria Si Factory"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    database_url: str = "sqlite:///./data/content_factory.db"

    comfyui_base_url: str = "http://127.0.0.1:8188"
    comfyui_client_id: str = "que-pasaria-si-factory"
    comfyui_video_workflow: Path = Path("workflows/video/ltx23_t2v_api.json")
    comfyui_tts_workflow: Path = Path("workflows/audio/chatterbox_tts_api.json")
    workflow_bindings_path: Path = Path("config/workflow_bindings.json")

    planner_provider: str = "mock"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"

    tts_provider: str = "silent"
    video_provider: str = "placeholder"
    tts_audio_format: str = "wav"
    tts_scene_mode: str = "per_scene"

    elevenlabs_enabled: bool = False
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_model_id: str = "eleven_multilingual_v2"
    elevenlabs_output_format: str = "mp3_44100_128"
    elevenlabs_stability: float = 0.45
    elevenlabs_similarity_boost: float = 0.75
    elevenlabs_style: float = 0.25
    elevenlabs_use_speaker_boost: bool = True
    elevenlabs_timeout_seconds: float = 120.0
    elevenlabs_fallback_to_comfyui: bool = True

    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_send_as_video: bool = True

    scene_duration_seconds: int = Field(default=4, validation_alias=AliasChoices("SCENE_DURATION_SECONDS"))
    default_video_duration_seconds: int = Field(default=60, validation_alias=AliasChoices("DEFAULT_VIDEO_DURATION_SECONDS", "VIDEO_DURATION_SECONDS"))
    default_scene_count: int = 15
    default_width: int = Field(default=1280, validation_alias=AliasChoices("DEFAULT_WIDTH", "VIDEO_WIDTH"))
    default_height: int = Field(default=720, validation_alias=AliasChoices("DEFAULT_HEIGHT", "VIDEO_HEIGHT"))
    default_fps: int = Field(default=25, validation_alias=AliasChoices("DEFAULT_FPS", "VIDEO_FPS"))
    default_language: str = "es"
    default_aspect_ratio: str = "16:9"

    max_parallel_video_jobs: int = 1
    ffmpeg_path: str = "ffmpeg"
    log_file: Path = Path("logs/app.log")
    data_dir: Path = Path("data")
    jobs_dir: Path = Path("data/jobs")

    comfyui_timeout_seconds: float = Field(default=5.0, ge=1.0)
    comfyui_poll_interval_seconds: float = Field(default=2.0, ge=0.25)
    comfyui_max_wait_seconds: float = Field(default=900.0, ge=1.0)
    comfyui_retries: int = Field(default=2, ge=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
