import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Завантажуємо .env
load_dotenv()

# Токен і адмін
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # якщо не вказано — 0

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не знайдено! Додай в Environment Variables на Render")

# Правильна ініціалізація бота (aiogram 3.13+)
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# === Простий старт для тесту ===
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "ПДР Тест Бот запущений!\n\n"
        "Ти в преміум-боті @PDR_RealTest_bot\n"
        "Тести ПДР 2025 — як у сервісному центрі МВС\n\n"
        "Оплата і повна версія — скоро тут!",
        disable_web_page_preview=True
    )

# === Пінг для UptimeRobot (щоб не засинав) ===
@dp.message(F.text == "/ping")
async def ping(message: types.Message):
    await message.answer("pong")

# === Головна функція ===
async def main():
    logging.info("ПДР RealTest Bot запущено!")
    # Для Web Service на Render — просто polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
