import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher
from aiohttp import web

TOKEN = "8982225070:AAHP4HB2yg6_m1pgldhtaxJNHBdJ_F0XDrk"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Простейший веб-сервер для обмана Render Port Scan
async def handle_ping(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    # Запускаем веб-сервер и опрос бота одновременно
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
