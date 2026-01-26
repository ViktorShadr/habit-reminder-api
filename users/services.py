import logging
from typing import Optional

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    """Сервис для отправки уведомлений через внутренний API Telegram-бота."""

    def __init__(self) -> None:
        # Важно: это URL именно FastAPI-сервиса бота, который принимает POST /send/
        self.telegram_api_base_url: Optional[str] = getattr(settings, "TELEGRAM_API_BASE_URL", None)

        # Секрет для внутреннего API (бот проверяет X-BOT-SECRET)
        self.bot_secret: Optional[str] = getattr(settings, "TELEGRAM_BOT_SECRET", None)

        if not self.telegram_api_base_url:
            logger.warning("TELEGRAM_API_BASE_URL не настроен (например: http://127.0.0.1:8001)")
        if not self.bot_secret:
            logger.warning("TELEGRAM_BOT_SECRET не настроен")

    def send_message(self, telegram_id: str, message: str) -> bool:
        """
        Отправляет сообщение через внутренний API Telegram-бота (FastAPI).

        Ожидается эндпоинт:
        POST {TELEGRAM_API_BASE_URL}/send/
        headers: X-BOT-SECRET
        body: {"telegram_id": "...", "message": "..."}
        """
        if not self.telegram_api_base_url:
            logger.error("TELEGRAM_API_BASE_URL не настроен — отправка невозможна")
            return False

        if not self.bot_secret:
            logger.error("TELEGRAM_BOT_SECRET не настроен — отправка невозможна")
            return False

        url = f"{self.telegram_api_base_url.rstrip('/')}/send/"
        payload = {"telegram_id": telegram_id, "message": message}
        headers = {
            "X-BOT-SECRET": self.bot_secret,
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, json=payload, headers=headers)

            if 200 <= response.status_code < 300:
                logger.info("Сообщение успешно отправлено пользователю %s", telegram_id)
                return True

            logger.error(
                "Ошибка отправки пользователю %s: статус=%s, ответ=%s",
                telegram_id,
                response.status_code,
                response.text,
            )
            return False

        except httpx.RequestError as e:
            logger.error("Ошибка сети при отправке пользователю %s: %s", telegram_id, e)
            return False
        except Exception as e:
            logger.exception("Неожиданная ошибка при отправке пользователю %s: %s", telegram_id, e)
            return False


# ---- Ленивая (lazy) инициализация, чтобы не фиксировать settings при импорте ----

_telegram_service: Optional[TelegramNotificationService] = None


def get_telegram_service() -> TelegramNotificationService:
    """
    Возвращает singleton сервиса с ленивым созданием.
    Полезно для Celery worker/beat, чтобы не ловить рассинхрон env/settings при импорте.
    """
    global _telegram_service
    if _telegram_service is None:
        _telegram_service = TelegramNotificationService()
    return _telegram_service
