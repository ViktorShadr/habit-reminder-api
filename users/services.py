import logging
from typing import Dict

import httpx
from django.conf import settings

from habits.notifications import format_habit_message

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    """Сервис для отправки уведомлений через Telegram."""

    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.backend_url = getattr(
            settings,
            "BACKEND_BASE_URL",
            "http://127.0.0.1:8002",
        )
        self.bot_secret = settings.TELEGRAM_BOT_SECRET

        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN не настроен")
        if not self.bot_secret:
            logger.warning("TELEGRAM_BOT_SECRET не настроен")

    def send_message(self, telegram_id: str, message: str) -> bool:
        """
        Отправляет сообщение через внутренний API Telegram бота.
        
        Args:
            telegram_id: ID пользователя в Telegram
            message: Текст сообщения
            
        Returns:
            True если отправка успешна, False в противном случае
        """
        if not self.bot_secret:
            logger.error("TELEGRAM_BOT_SECRET не настроен")
            return False

        try:
            # URL внутреннего API бота
            url = f"{self.backend_url}/send/"

            payload = {
                "telegram_id": telegram_id,
                "message": message
            }

            headers = {
                "X-BOT-SECRET": self.bot_secret,
                "Content-Type": "application/json"
            }

            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                logger.info(f"Сообщение успешно отправлено пользователю {telegram_id}")
                return True
            else:
                logger.error(f"Ошибка отправки сообщения пользователю {telegram_id}: "
                             f"статус {response.status_code}, ответ: {response.text}")
                return False

        except httpx.RequestError as e:
            logger.error(f"Ошибка сети при отправке сообщения пользователю {telegram_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке сообщения пользователю {telegram_id}: {e}")
            return False

    def send_habit_reminder(self, telegram_id: str, habit_data: Dict) -> bool:
        """
        Отправляет напоминание о привычке.
        
        Args:
            telegram_id: ID пользователя в Telegram
            habit_data: Данные о привычке
            
        Returns:
            True если отправка успешна, False в противном случае
        """
        message = format_habit_message(habit_data)
        return self.send_message(telegram_id, message)


# Глобальный экземпляр сервиса
telegram_service = TelegramNotificationService()
