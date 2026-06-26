import asyncio
import time
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings
from app.services.workflow import WorkflowConfigurationError, apply_video_bindings, load_json_file, load_workflow_bindings, validate_video_bindings


class ComfyUIError(RuntimeError):
    pass


class ComfyUIClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(base_url=self.settings.comfyui_base_url, timeout=self.settings.comfyui_timeout_seconds) as client:
                response = await client.get("/system_stats")
                return response.status_code < 500
        except httpx.HTTPError:
            return False

    async def submit_workflow(self, workflow: dict[str, Any]) -> str:
        payload = {"prompt": workflow, "client_id": self.settings.comfyui_client_id}
        async with httpx.AsyncClient(base_url=self.settings.comfyui_base_url, timeout=self.settings.comfyui_timeout_seconds) as client:
            response = await client.post("/prompt", json=payload)
            if response.status_code >= 400:
                raise ComfyUIError(f"ComfyUI rechazo el workflow: HTTP {response.status_code} {response.text}")
            data = response.json()
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise ComfyUIError("ComfyUI no devolvio prompt_id.")
        return str(prompt_id)

    async def wait_for_history(self, prompt_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.settings.comfyui_max_wait_seconds
        async with httpx.AsyncClient(base_url=self.settings.comfyui_base_url, timeout=self.settings.comfyui_timeout_seconds) as client:
            while time.monotonic() < deadline:
                response = await client.get(f"/history/{prompt_id}")
                response.raise_for_status()
                history = response.json()
                if prompt_id in history:
                    return history[prompt_id]
                await asyncio.sleep(self.settings.comfyui_poll_interval_seconds)
        raise ComfyUIError(f"Tiempo agotado esperando history/{prompt_id}.")

    async def generate_video(
        self,
        *,
        prompt: str,
        width: int,
        height: int,
        duration: int,
        fps: int,
        seed: int,
        filename_prefix: str,
    ) -> tuple[str, dict[str, Any]]:
        workflow_path = self.settings.comfyui_video_workflow
        bindings_path = self.settings.workflow_bindings_path
        try:
            workflow = load_json_file(workflow_path)
            bindings = load_workflow_bindings(bindings_path)
            validate_video_bindings(workflow, bindings)
            prepared = apply_video_bindings(
                workflow,
                bindings,
                prompt=prompt,
                width=width,
                height=height,
                duration=duration,
                fps=fps,
                seed=seed,
                filename_prefix=filename_prefix,
            )
        except WorkflowConfigurationError:
            raise
        except Exception as exc:
            raise WorkflowConfigurationError(f"No se pudo preparar el workflow de video: {exc}") from exc

        last_error: Exception | None = None
        for attempt in range(self.settings.comfyui_retries + 1):
            try:
                prompt_id = await self.submit_workflow(prepared)
                history = await self.wait_for_history(prompt_id)
                return prompt_id, history
            except Exception as exc:
                last_error = exc
                if attempt >= self.settings.comfyui_retries:
                    break
                await asyncio.sleep(1 + attempt)
        raise ComfyUIError(f"Fallo ComfyUI tras reintentos: {last_error}") from last_error

    @staticmethod
    def find_generated_video(history: dict[str, Any]) -> dict[str, Any] | None:
        outputs = history.get("outputs", {})
        if not isinstance(outputs, dict):
            return None
        for node_output in outputs.values():
            if not isinstance(node_output, dict):
                continue
            for key in ("videos", "gifs", "images"):
                items = node_output.get(key)
                if not isinstance(items, list):
                    continue
                for item in items:
                    if isinstance(item, dict) and item.get("filename"):
                        return item
        return None

    async def download_output_file(self, output: dict[str, Any], destination: Path) -> Path:
        filename = output.get("filename")
        if not filename:
            raise ComfyUIError("La salida de ComfyUI no contiene filename.")
        params = {
            "filename": filename,
            "subfolder": output.get("subfolder") or "",
            "type": output.get("type") or "output",
        }
        destination.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(base_url=self.settings.comfyui_base_url, timeout=self.settings.comfyui_timeout_seconds) as client:
            response = await client.get("/view", params=params)
            response.raise_for_status()
        destination.write_bytes(response.content)
        return destination
