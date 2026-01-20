import asyncio
import os
from typing import Dict

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from dotenv import load_dotenv

from main import send_notification_to_user

load_dotenv()

# Проверяем секрет для API
BOT_SECRET = os.getenv("TELEGRAM_BOT_SECRET")
if not BOT_SECRET:
    raise RuntimeError("Не задан TELEGRAM_BOT_SECRET")

app = FastAPI(title="Telegram Bot API")


class TelegramMessage(BaseModel):
    telegram_id: str
    message: str


@app.post("/send/")
async def send_message(message_data: TelegramMessage, x_bot_secret: str = None):
    """
    Отправляет сообщение пользователю в Telegram.
    
    Args:
        message_data: Данные для отправки сообщения
        x_bot_secret: Секретный ключ для аутентификации
        
    Returns:
        Результат отправки
    """
    # Проверяем секрет
    if x_bot_secret != BOT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Неверный секретный ключ"
        )
    
    # Отправляем сообщение
    success = await send_notification_to_user(
        telegram_id=message_data.telegram_id,
        message=message_data.message
    )
    
    if success:
        return {"status": "success", "message": "Сообщение отправлено"}
    else:
        return {"status": "error", "message": "Ошибка отправки сообщения"}


@app.get("/health/")
async def health_check():
    """Проверка работоспособности API."""
    return {"status": "healthy"}
