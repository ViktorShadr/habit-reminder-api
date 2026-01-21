import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, status
from pydantic import BaseModel

from telegram_bot.main import send_notification_to_user  # поправь импорт под свою структуру

load_dotenv()

BOT_SECRET = os.getenv("TELEGRAM_BOT_SECRET")
if not BOT_SECRET:
    raise RuntimeError("Не задан TELEGRAM_BOT_SECRET")

app = FastAPI(title="Telegram Bot API")


class TelegramMessage(BaseModel):
    telegram_id: str
    message: str


@app.post("/send/")
async def send_message(
    message_data: TelegramMessage,
    x_bot_secret: str | None = Header(default=None, alias="X-BOT-SECRET"),
):
    """
    Отправляет сообщение пользователю в Telegram.
    Заголовок: X-BOT-SECRET: <secret>
    """
    if x_bot_secret != BOT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Неверный секретный ключ",
        )

    success = await send_notification_to_user(
        telegram_id=message_data.telegram_id,
        message=message_data.message,
    )

    if success:
        return {"status": "success", "message": "Сообщение отправлено"}

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Ошибка отправки сообщения",
    )


@app.get("/health/")
async def health_check():
    return {"status": "healthy"}
