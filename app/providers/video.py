import random
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import Settings
from app.services.comfyui import ComfyUIClient


class GeneratedVideoResult:
    def __init__(self, path: Path, prompt_id: str | None, seed: int, generation_seconds: float):
        self.path = path
        self.prompt_id = prompt_id
        self.seed = seed
        self.generation_seconds = generation_seconds


class VideoProvider(ABC):
    @abstractmethod
    async def generate_scene_video(
        self,
        *,
        visual_prompt: str,
        width: int,
        height: int,
        duration_seconds: int,
        fps: int,
        output_path: Path,
        filename_prefix: str,
    ) -> GeneratedVideoResult:
        raise NotImplementedError


class PlaceholderVideoProvider(VideoProvider):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def generate_scene_video(
        self,
        *,
        visual_prompt: str,
        width: int,
        height: int,
        duration_seconds: int,
        fps: int,
        output_path: Path,
        filename_prefix: str,
    ) -> GeneratedVideoResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        seed = random.randint(1, 2_147_483_647)
        start = time.monotonic()
        hue = seed % 360
        command = [
            self.settings.ffmpeg_path,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size={width}x{height}:rate={fps}:duration={duration_seconds}",
            "-vf",
            f"hue=h={hue}",
            "-t",
            str(duration_seconds),
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"FFmpeg no pudo crear el video placeholder: {completed.stderr.strip()}")
        return GeneratedVideoResult(output_path, "placeholder", seed, time.monotonic() - start)


class ComfyUIVideoProvider(VideoProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = ComfyUIClient(settings)

    async def generate_scene_video(
        self,
        *,
        visual_prompt: str,
        width: int,
        height: int,
        duration_seconds: int,
        fps: int,
        output_path: Path,
        filename_prefix: str,
    ) -> GeneratedVideoResult:
        seed = random.randint(1, 2_147_483_647)
        start = time.monotonic()
        prompt_id, history = await self.client.generate_video(
            prompt=visual_prompt,
            width=width,
            height=height,
            duration=duration_seconds,
            fps=fps,
            seed=seed,
            filename_prefix=filename_prefix,
        )
        generated_output = self.client.find_generated_video(history)
        if generated_output is None:
            raise RuntimeError(f"ComfyUI termino el prompt {prompt_id}, pero no se encontro un video en history.")
        await self.client.download_output_file(generated_output, output_path)
        return GeneratedVideoResult(output_path, prompt_id, seed, time.monotonic() - start)


def get_video_provider(settings: Settings) -> VideoProvider:
    if settings.video_provider.lower() == "comfyui":
        return ComfyUIVideoProvider(settings)
    return PlaceholderVideoProvider(settings)
