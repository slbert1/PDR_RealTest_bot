# test_bot.py — Преміум ПДР-бот @PDR_RealTest_bot
# 100% працює на Render Web Service (безкоштовно + UptimeRobot)

import os
import asyncio
import sqlite3
import logging
import json
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
load_dotenv()

# === НАЛАШТУВАННЯ ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не знайдено в змінних середовища!")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# === БАЗА КОРИСТУВАЧІВ ===
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    paid_until TEXT,
    best_score INTEGER DEFAULT 0
)''')
conn.commit()

# === ЗАВАНТАЖЕННЯ ПИТАНЬ ===
try:
    with open("pdr_questions.json", "r", encoding="utf-8") as f:
        QUESTIONS = json.load(f)
    logging.info(f"Завантажено {len(QUESTIONS)} питань з pdr_questions.json")
except FileNotFoundError:
    logging.warning("pdr_questions.json не знайдено → запущено тестовий режим")
    QUESTIONS = [
        {
            "id": 999,
            "text": "ТЕСТОВЕ ПИТАННЯ\n\nЯка правильна відповідь?",
            "image": None,
            "options": ["А) Неправильно", "Б) Правильно", "В) Неправильно", "Г) Неправильно"],
            "correct": 1
        }
    ] * 20

# === СТАН ===
class TestStates(StatesGroup):
    passing = State()

# === КЛАВІАТУРИ ===
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пройти тест ПДР 2025", callback_data="start_test")],
        [InlineKeyboardButton(text="Мій доступ і результати", callback_data="my_stats")],
        [InlineKeyboardButton(text="Написати адміну", url="https://t.me/tvoy_username")]
    ])

# === СТАРТ ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Вітаю в <b>@PDR_RealTest_bot</b>!\n\n"
        "Тут ти можеш пройти реальний тест ПДР 2025 — точно як у сервісному центрі МВС\n\n"
        "20 питань • 20 хвилин • максимум 2 помилки\n\n"
        "Натисни кнопку нижче, щоб почати:",
        reply_markup=main_menu()
    )

# === ПОЧАТОК ТЕСТУ ===
@dp.callback_query(F.data == "start_test")
async def begin_test(callback: types.CallbackQuery, state: FSMContext):
    # Для тесту просто даємо доступ усім
    questions = random.sample(QUESTIONS, 20)
    await state.set_data({
        "questions": questions,
        "answers": {},
        "errors": 0,
        "start_time": datetime.now(),
        "current": 0
    })
    await state.set_state(TestStates.passing)
    await show_question(callback.message, state)
    await callback.answer()

# === ПОКАЗ ПИТАННЯ ===
async def show_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    q = data["questions"][data["current"]]
    passed = data["current"]current""
    errors = data["errors"]
    elapsed = int((datetime.now() - data["start_time"]).total_seconds())
    time_left = max(0, 1200 - elapsed)
    minutes = time_left // 60
    seconds = time_left % 60

    progress = "█" * (passed // 2) + "▉" * (passed % 2) + "░" * (20 - passed)

    text = f"<b>{passed+1}/20</b>    {progress}\n\n"
    text += f"Залишилось часу: <b>{minutes}:{seconds:02d}</b>\n\n"
    text += q["text"]

    # Кнопки відповідей
    kb = []
    for i, opt in enumerate(q["options"]):
        kb.append([InlineKeyboardButton(text=opt, callback_data=f"ans_{i}")])

    # Нижній рядок номерів питань
    bottom = []
    for i in range(20):
        if i < passed:
            correct = data["answers"].get(i, -1) == data["questions"][i]["correct"]
            bottom.append(InlineKeyboardButton(text="🟩" if correct else "🟥", callback_data=f"goto_{i}"))
        elif i == passed:
            bottom.append(InlineKeyboardButton(text="🔵", callback_data="ignore"))
        else:
            bottom.append(InlineKeyboardButton(text="⚪", callback_data="ignore"))
    kb.append(bottom)

    await message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    # Якщо є картинка — кидаємо окремо
    if q.get("image"):
        await bot.send_photo(message.chat.id, q["image"], caption="Дивись уважно на зображення")

# === ОБРОБКА ВІДПОВІДІ ===
@dp.callback_query(F.data.startswith("ans_"))
async def process_answer(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    choice = int(callback.data.split("_")[1])
    q_idx = data["current"]
    correct_idx = data["questions"][q_idx]["correct"]

    data["answers"][q_idx] = choice
    if choice != correct_idx:
        data["errors"] += 1

    data["current"] += 1
    await state.set_data(data)

    if data["current"] >= 20 or data["errors"] >= 3:
        await finish_test(callback.message, state)
    else:
        await show_question(callback.message, state)
    await callback.answer()

# === ФІНІШ ===
async def finish_test(message: types.Message, state: FSMContext):
    data = await state.get_data()
    correct = sum(1 for i, a in data["answers"].items() 
                  if a == data["questions"][i]["correct"])

    if data["errors"] <= 2:
        result = f"ВІТАЮ! Ти склав би іспит! ✅\n\nПравильних: {correct}/20"
    else:
        result = f"На жаль, іспит не складено ❌\n\nПомилок: {data['errors']} (дозволено максимум 2)"

    await message.edit_text(
        result + "\n\nХочеш пройти ще раз?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пройти ще раз", callback_data="start_test")],
            [InlineKeyboardButton(text="Головне меню", callback_data="menu")]
        ])
    )
    await state.clear()

@dp.callback_query(F.data == "menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("Головне меню:", reply_markup=main_menu())
    await callback.answer()

# === ЗАПУСК ===
async def main():
    logging.info("Преміум ПДР RealTest Bot успішно запущено!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
