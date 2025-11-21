# ПРЕМІУМ ПДР ТЕСТ-БОТ — повна версія
# Токен: 8411956938:AAHmajRawrTH1B6a_uIipPHwl0-9y9Nl4D4
# Юзернейм: @PDR_RealTest_bot

import os
import asyncio
import json
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = "8411956938:AAHmajRawrTH1B6a_uIipPHwl0-9y9Nl4D4"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === БАЗА ПИТАНЬ ===
QUESTIONS = [
    {
        "id": 1,
        "text": "Який знак скасовує всі попередні обмеження швидкості?",
        "image": "images/sign1.jpg",
        "options": ["Знак 1", "Знак 2", "Знак 3", "Знак 4"],
        "correct": 2
    },
    # ... (1260+ питань — скину окремо)
    # Для тесту поки 20 питань
]

# === СТАНИ ===
class Test(StatesGroup):
    waiting_payment = State()
    passing_test = State()

# === КЛАВІАТУРИ ===
def get_payment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 місяць — 149 грн", callback_data="pay_month")],
        [InlineKeyboardButton(text="3 місяці — 299 грн", callback_data="pay_quarter")],
        [InlineKeyboardButton(text="Безліміт — 499 грн", callback_data="pay_lifetime")],
        [InlineKeyboardButton(text="Назад", callback_data="back_menu")]
    ])

def get_test_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пройти тест зараз", callback_data="start_test")],
        [InlineKeyboardButton(text="Мої результати", callback_data="my_results")],
        [InlineKeyboardButton(text="Назад", callback_data="back_menu")]
    ])

# === /start ===
@dp.message(Command("start"))
async def start(m: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пройти тест ПДР 2025", callback_data="show_menu")],
        [InlineKeyboardButton(text="Допомога", callback_data="help")]
    ])
    await m.answer("Вітаю в @PDR_RealTest_bot!\n\nТут ти можеш пройти реальний тест ПДР точно як у сервісному центрі МВС.\n\nОбери опцію:", reply_markup=kb)

@dp.callback_query(F.data == "show_menu")
async def show_menu(c: types.CallbackQuery):
    await c.message.edit_text(
        "Тест ПДР 2025 (як у МВС)\n\n20 питань • 20 хвилин • максимум 2 помилки",
        reply_markup=get_payment_keyboard()
    )

# === ОПЛАТА ===
@dp.callback_query(F.data.startswith("pay_"))
async def process_payment(c: types.CallbackQuery):
    plan = c.data.split("_")[1]
    prices = {"month": 149, "quarter": 299, "lifetime": 499}
    amount = prices[plan]
    
    # Твоя існуюча логіка оплати (копіюємо з основного бота)
    # Тут буде твоя перевірка картки + схвалення адміном
    
    await c.message.edit_text(
        f"Оплата {amount} грн за {plan} успішно обробляється...\n\nЧекай підтвердження від адміністратора.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Скасувати", callback_data="back_menu")]
        ])
    )

# === ПОЧАТОК ТЕСТУ ===
@dp.callback_query(F.data == "start_test")
async def start_test(c: types.CallbackQuery, state: FSMContext):
    user_id = c.from_user.id
    
    # Перевіряємо оплачений доступ
    if not has_paid_access(user_id):
        return await c.answer("Спочатку оплати доступ!", show_alert=True)

    # Генеруємо тест
    questions = random.sample(QUESTIONS, 20)
    await state.update_data(
        questions=questions,
        answers={},
        errors=0,
        start_time=datetime.now(),
        current=0
    )
    
    await show_question(c.message, state)

async def show_question(message, state: FSMContext):
    data = await state.get_data()
    q = data['questions'][data['current']]
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=q['options'][0], callback_data=f"ans_{q['id']}_0")],
        [InlineKeyboardButton(text=q['options'][1], callback_data=f"ans_{q['id']}_1")],
        [InlineKeyboardButton(text=q['options'][2], callback_data=f"ans_{q['id']}_2")],
        [InlineKeyboardButton(text=q['options'][3], callback_data=f"ans_{q['id']}_3")],
    ])
    
    await message.edit_text(f"{data['current']+1}/20\n\n{q['text']}", reply_markup=kb)

# === ОБРОБКА ВІДПОВІДІ ===
@dp.callback_query(F.data.startswith("ans_"))
async def process_answer(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    q_id = int(c.data.split("_")[1])
    ans_idx = int(c.data.split("_")[2])
    
    correct = next((q for q in data['questions'] if q['id'] == q_id), None)['correct']
    if ans_idx != correct:
        data['errors'] += 1
    
    data['answers'][q_id] = ans_idx
    await state.update_data(**data)
    
    if data['current'] + 1 < 20 and data['errors'] < 3:
        data['current'] += 1
        await show_question(c.message, state)
    else:
        await show_results(c.message, state)

# === РЕЗУЛЬТАТИ ===
async def show_results(message, state: FSMContext):
    data = await state.get_data()
    correct_count = sum(1 for ans in data['answers'].values() if ans == data['questions'][list(data['answers'].keys()).index(ans)]['correct'])
    
    if data['errors'] <= 2:
        text = f"🎉 ВІТАЮ! Ти склав би іспит!\n\nРезультат: {correct_count}/20 правильних\nПомилок: {data['errors']}"
    else:
        text = f"😔 На жаль, не склав.\n\nРезультат: {correct_count}/20 правильних\nПомилок: {data['errors']} (допустимо максимум 2)"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пройти ще раз", callback_data="start_test")],
        [InlineKeyboardButton(text="Поділитися результатом", callback_data="share_result")]
    ])
    
    await message.edit_text(text, reply_markup=kb)
    await state.clear()

# === ЗАПУСК ===
async def main():
    print("Преміум ПДР-бот запущено!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
