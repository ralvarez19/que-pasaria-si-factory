import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TelegramSendResult:
    ok: bool
    status: str
    method: str | None = None
    video_path: str | None = None
    error: str | None = None
    telegram_message_id: int | None = None
    response: dict[str, Any] | None = None


class TelegramNotifier:
    def __init__(self, settings: Settings):
        self.settings = settings

    def is_configured(self) -> bool:
        return bool(
            self.settings.telegram_enabled
            and self.settings.telegram_bot_token.strip()
            and self.settings.telegram_chat_id.strip()
        )

    def configuration_error(self) -> str | None:
        if not self.settings.telegram_enabled:
            return "Telegram deshabilitado"
        if not self.settings.telegram_bot_token.strip():
            return "Falta TELEGRAM_BOT_TOKEN"
        if not self.settings.telegram_chat_id.strip():
            return "Falta TELEGRAM_CHAT_ID"
        return None

    def masked_chat_id(self) -> str:
        chat_id = self.settings.telegram_chat_id.strip()
        if not chat_id:
            return "<missing>"
        if len(chat_id) <= 4:
            return "*" * len(chat_id)
        return f"{chat_id[:3]}...{chat_id[-2:]}"

    async def send_video(self, video_path: Path, caption: str) -> TelegramSendResult:
        video_path = Path(video_path)
        configuration_error = self.configuration_error()
        if configuration_error:
            logger.warning("Telegram no configurado: %s chat_id=%s", configuration_error, self.masked_chat_id())
            return TelegramSendResult(ok=False, status="disabled" if not self.settings.telegram_enabled else "failed", video_path=str(video_path), error=configuration_error)

        if not video_path.exists():
            error = f"El video no existe: {video_path}"
            logger.error("Telegram envio cancelado: %s", error)
            return TelegramSendResult(ok=False, status="failed", video_path=str(video_path), error=error)

        size_bytes = video_path.stat().st_size
        logger.info("Telegram envio iniciado video=%s size_bytes=%s chat_id=%s", video_path, size_bytes, self.masked_chat_id())

        first_method = "sendVideo" if self.settings.telegram_send_as_video else "sendDocument"
        first_result = await self._send_file(first_method, video_path, caption)
        if first_result.ok:
            return first_result

        if first_method == "sendVideo":
            logger.warning("Telegram sendVideo fallo, reintentando como documento: %s", first_result.error)
            fallback_result = await self._send_file("sendDocument", video_path, caption)
            if fallback_result.ok:
                return fallback_result
            return fallback_result

        return first_result

    async def send_message(self, text: str) -> TelegramSendResult:
        configuration_error = self.configuration_error()
        if configuration_error:
            return TelegramSendResult(ok=False, status="disabled" if not self.settings.telegram_enabled else "failed", error=configuration_error)
        url = self._api_url("sendMessage")
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, data={"chat_id": self.settings.telegram_chat_id.strip(), "text": text})
            return self._result_from_response(response, "sendMessage", None)
        except httpx.HTTPError as exc:
            logger.exception("Telegram sendMessage fallo: %s", exc)
            return TelegramSendResult(ok=False, status="failed", method="sendMessage", error=str(exc))

    async def _send_file(self, method: str, video_path: Path, caption: str) -> TelegramSendResult:
        field_name = "video" if method == "sendVideo" else "document"
        url = self._api_url(method)
        try:
            with video_path.open("rb") as file_handle:
                files = {field_name: (video_path.name, file_handle, "video/mp4")}
                data = {"chat_id": self.settings.telegram_chat_id.strip(), "caption": caption}
                async with httpx.AsyncClient(timeout=300) as client:
                    response = await client.post(url, data=data, files=files)
            return self._result_from_response(response, method, video_path)
        except httpx.HTTPError as exc:
            logger.exception("Telegram %s fallo por error HTTP: %s", method, exc)
            return TelegramSendResult(ok=False, status="failed", method=method, video_path=str(video_path), error=str(exc))

    def _result_from_response(self, response: httpx.Response, method: str, video_path: Path | None) -> TelegramSendResult:
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}

        if response.is_success and payload.get("ok", True):
            message_id = None
            result_payload = payload.get("result")
            if isinstance(result_payload, dict):
                message_id = result_payload.get("message_id")
            logger.info("Telegram %s exitoso status_code=%s message_id=%s", method, response.status_code, message_id)
            return TelegramSendResult(
                ok=True,
                status="sent",
                method=method,
                video_path=str(video_path) if video_path else None,
                telegram_message_id=message_id,
                response=payload,
            )

        description = payload.get("description") if isinstance(payload, dict) else None
        error = description or f"HTTP {response.status_code}"
        logger.error("Telegram %s fallo status_code=%s error=%s", method, response.status_code, error)
        return TelegramSendResult(
            ok=False,
            status="failed",
            method=method,
            video_path=str(video_path) if video_path else None,
            error=error,
            response=payload if isinstance(payload, dict) else None,
        )

    def _api_url(self, method: str) -> str:
        token = self.settings.telegram_bot_token.strip()
        return f"https://api.telegram.org/bot{token}/{method}"
