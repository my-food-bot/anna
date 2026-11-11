import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher

# Ваш токен
TOKEN = "8982225070:AAGYrcuB69vBOPrTv3sCTe03VX3GTvIR1ww"

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def main():
    # Запуск получения сообщений
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
