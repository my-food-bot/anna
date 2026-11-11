import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher

# Ваш токен
TOKEN = "8982225070:AAHP4HB2yg6_m1pgldhtaxJNHBdJ_F0XDrk"

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def main():
    # Запуск получения сообщений
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
