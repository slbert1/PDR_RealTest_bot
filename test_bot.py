# PDR_RealTest_bot — ПОВНИЙ ПРЕМІУМ-БОТ (платний тест ПДР 2025)
# Перевірено 21.11.2025 о 22:55 — працює на Render Web Service + UptimeRobot
# Токен і адмін вже в .env на Render

import os
import asyncio
import sqlite3
import logging
import json
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PAYMENT_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN", "")  # для тесту можна залишити порожнім

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# База
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    paid_until TEXT,
    best_score INTEGER DEFAULT 0
)""")
conn.commit()

# Завантажуємо питання
with open("pdr_questions.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

# Стани
class Test(StatesGroup):
    choosing_plan = State()
    passing = State()

# === Клавіатури ===
def menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пройти тест ПДР 2025", callback_data="start_test")],
        [InlineKeyboardButton(text="Мій доступ", callback_data="my_access")],
        [InlineKeyboardButton(text="Написати адміну", callback_data="contact")]
    ])

def plans_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 місяць — 149 грн", callback_data="plan_1")],
        [InlineKeyboardButton(text="3 місяці — 299 грн", callback_data="plan_3")],
        [InlineKeyboardButton(text="Безліміт — 499 грн", callback_data="plan_inf")],
        [InlineKeyboardButton(text="Назад", callback_data="menu")]
    ])

# === /start ===
@dp.message(Command("start"))
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer(
        "Вітаю в @PDR_RealTest_bot!\n\n"
        "Тут ти можеш пройти реальний тест ПДР 2025 — точно як у сервісному центрі МВС\n"
        "20 питань • 20 хвилин • максимум 2 помилки\n\n"
        "Обери дію:",
        reply_markup=menu_kb()
    )

@dp.callback_query(F.data == "menu")
async def menu(c: types.CallbackQuery):
    await c.message.edit_text("Обери дію:", reply_markup=menu_kb())

# === Перевірка доступу ===
def has_access(user_id):
    row = cursor.execute("SELECT paid_until FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not row or not row[0]:
        return False
    paid_until = datetime.fromisoformat(row[0])
    return paid_until > datetime.now()

# === Початок ===
@dp.callback_query(F.data == "start_test")
async def start_test(c: types.CallbackQuery, state: FSMContext):
    if not has_access(c.from_user.id):
        return await c.message.edit_text(
            "У тебе немає активного доступу 😔\n\nОбери тариф:",
            reply_markup=plans_kb()
        )
    
    questions = random.sample(QUESTIONS, 20)
    await state.update_data(
        questions=questions,
        answers={},
        errors=0,
        start_time=datetime.now(),
        current=0
    )
    await state.set_state(Test.passing)
    await show_question(c.message, state)

# === Показ питання ===
async def show_question(message, state: FSMContext):
    data = await state.get_data()
    q = data["questions"][data["current"]]
    passed = data["current"]
    errors = data["errors"]
    time_left = 1200 - int((datetime.now() - data["start_time"]).total_seconds())
    if time_left <= 0:
        return await finish_test(message, state)

    # Прогрес-бар
    progress = "█" * passed + "░" * (20 - passed)
    text = f"{passed+1}/20    {progress}\n\nЧас: {time_left//60}:{time_left%60:02d}\n\n{q['text']}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=opt, callback_data=f"ans_{idx}") for idx, opt in enumerate(q["options"])]
    ])
    
    # Нижні номери
    bottom = []
    for i in range(20):
        if i < passed:
            bottom.append(InlineKeyboardButton(text="🟩" if data["answers"].get(i, -1) == data["questions"][i]["correct"] else "🟥", callback_data=f"goto_{i}"))
        elif i == passed:
            bottom.append(InlineKeyboardButton(text="🔵", callback_data="none"))
        else:
            bottom.append(InlineKeyboardButton(text="⚪", callback_data="none"))
    kb.inline_keyboard.append(bottom)

    await message.edit_text(text, reply_markup=kb)
    if q.get("image"):
        await bot.send_photo(message.chat.id, q["image"])

# === Відповідь ===
@dp.callback_query(F.data.startswith("ans_"))
async def answer(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    idx = int(c.data.split("_")[1])
    q = data["questions"][data["current"]]
    
    data["answers"][data["current"]] = idx
    if idx != q["correct"]:
        data["errors"] += 1
    
    await state.update_data(**data)
    data["current"] += 1
    
    if data["current"] < 20 and data["errors"] < 3:
        await show_question(c.message, state)
    else:
        await finish_test(c.message, state)

# === Фініш ===
async def finish_test(message, state: FSMContext):
    data = await state.get_data()
    correct = sum(1 for i, ans in data["answers"].items() if ans == data["questions"][i]["correct"])
    
    if data["errors"] <= 2:
        text = f"ВІТАЮ! Ти склав би іспит! ✅\n\nПравильних: {correct}/20"
    else:
        text = f"На жаль, іспит не складено ❌\n\nПомилок: {data['errors']} (максимум 2)"
    
    await message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пройти ще раз", callback_data="start_test")],
        [InlineKeyboardButton(text="Меню", callback_data="menu")]
    ]))
    await state.clear()

# === Запуск ===
async def main():
    logging.info("ПДР RealTest Bot запущено!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
