import os
import re
import asyncio

import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# Это URL твоего Django (где /api/users/telegram/confirm/)
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8001")
BOT_SECRET = os.getenv("TELEGRAM_BOT_SECRET")

if not BOT_TOKEN:
    raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN")
if not BOT_SECRET:
    raise RuntimeError("Не задан TELEGRAM_BOT_SECRET")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def confirm_telegram_link(code: str, chat_id: int) -> tuple[bool, str]:
    """Возвращает (ok, message)."""
    url = f"{BACKEND_BASE_URL}/api/users/telegram/confirm/"
    payload = {"code": code, "chat_id": chat_id}
    headers = {"X-BOT-SECRET": BOT_SECRET}

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(url, json=payload, headers=headers)

    if r.status_code == 200:
        return True, "Готово! Telegram успешно привязан ✅"
    if r.status_code == 403:
        return False, "Ошибка конфигурации бота (секрет не принят сервером)."

    try:
        data = r.json()
        detail = data.get("detail") or data
    except Exception:
        detail = r.text
    return False, f"Не получилось привязать. {detail}"


async def send_notification_to_user(telegram_id: str, message: str) -> bool:
    """Отправляет сообщение пользователю в Telegram."""
    try:
        await bot.send_message(chat_id=int(telegram_id), text=message)
        return True
    except Exception as e:
        print(f"Ошибка отправки сообщения пользователю {telegram_id}: {e}")
        return False


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    text = message.text or ""
    parts = text.strip().split(maxsplit=1)

    if len(parts) == 1:
        await message.answer(
            "Привет! Чтобы привязать аккаунт, получи код в сервисе и отправь мне:\n"
            "/start <КОД>\n\n"
            "Например:\n"
            "/start A1B2C3D4E5"
        )
        return

    code = parts[1].strip()

    if not re.fullmatch(r"[A-Z0-9]{6,32}", code):
        await message.answer("Код выглядит некорректно. Проверь и попробуй ещё раз.")
        return

    ok, reply = await confirm_telegram_link(code=code, chat_id=message.chat.id)
    await message.answer(reply)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
