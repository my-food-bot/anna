import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher

# Ваш токен
TOKEN = "9030937137:AAEEpbyNite1SgjelqX9J3q5c3vGZOKmT5o"

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def main():
    # Запуск получения сообщений
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
