import asyncio

import uvicorn

from api import app as api_app
from main import dp, bot


async def run_bot():
    """Запуск Telegram бота."""
    await dp.start_polling(bot)


async def run_api():
    """Запуск API для отправки сообщений."""
    config = uvicorn.Config(api_app, host="127.0.0.1", port=8001, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """Запуск бота и API одновременно."""
    # Запускаем обе задачи параллельно
    await asyncio.gather(
        run_bot(),
        run_api()
    )


if __name__ == "__main__":
    asyncio.run(main())
