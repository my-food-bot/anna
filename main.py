import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

TOKEN = "9030937137:AAEEpbyNite1SgjelqX9J3q5c3vGZOKmT5o"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Временное хранилище истории питания пользователей (в реальном проекте лучше БД, но для старта идеально)
user_history = {}

# Состояния для пошагового конструктора
class MealState(StatesGroup):
    waiting_for_training_day = State()
    choosing_meal_num = State()
    choosing_protein = State()
    choosing_carb = State()
    choosing_fat = State()
    custom_product_input = State()

# Базы данных продуктов (с примерным КБЖУ на порцию «на глаз»)
PROTEINS = {
    "Куриная грудка (~200г)": {"cals": 220, "p": 46, "f": 4, "c": 0},
    "Индейка (~200г)": {"cals": 230, "p": 44, "f": 5, "c": 0},
    "Говядина (~180г)": {"cals": 310, "p": 38, "f": 16, "c": 0},
    "Рыба / Лосось (~200г)": {"cals": 280, "p": 36, "f": 14, "c": 0},
    "Творог (~250г)": {"cals": 250, "p": 40, "f": 5, "c": 8},
}

CARBS = {
    "Рис / Гречка (готовые, ~200г)": {"cals": 260, "p": 6, "f": 2, "c": 55},
    "Макароны (готовые, ~200г)": {"cals": 280, "p": 8, "f": 2, "c": 52},
    "Картофель отварной (~250г)": {"cals": 200, "p": 5, "f": 1, "c": 45},
    "Хлеб цельнозерновой (2 куска)": {"cals": 140, "p": 6, "f": 2, "c": 24},
}

FATS_VEG = {
    "Оливковое масло (1 ст.л.)": {"cals": 120, "p": 0, "f": 14, "c": 0},
    "Авокадо (половинка, ~80г)": {"cals": 130, "p": 1, "f": 12, "c": 4},
    "Орехи (горсть, ~30г)": {"cals": 180, "p": 5, "f": 16, "c": 5},
    "Свежие овощи (салат без масла, миска)": {"cals": 40, "p": 2, "f": 0, "c": 8},
}

# Клавиатура возврата
def back_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад / Отменить", callback_data="cancel_action")
    return builder.as_markup()

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="🏋️ Тренировочный день", callback_data="train_yes")
    builder.button(text="🛋️ День отдыха", callback_data="train_no")
    builder.adjust(1)
    
    await message.answer(
        "Привет! Я твой быстрый конструктор питания.\n"
        "У тебя все 3 приема пищи имеют одинаковый калораж — это упростит задачу!\n\n"
        "Сначала ответь: **сегодня день тренировки?**",
        reply_markup=builder.as_markup()
    )
    await state.set_state(MealState.waiting_for_training_day)

@dp.callback_query(F.data.startswith("train_"))
async def process_training_day(callback: types.CallbackQuery, state: FSMContext):
    is_training = "yes" in callback.data
    await state.update_data(is_training=is_training, current_meal=1, meal_data=[])
    
    day_type = "Тренировочный день 🏋️" * is_training + "День отдыха 🛋️" * (not is_training)
    await callback.message.edit_text(f"Отлично! Режим: **{day_type}**.\n\nДавай соберем **Прием пищи №1**.\nВыбери основной белок:")
    
    builder = InlineKeyboardBuilder()
    for prod in PROTEINS.keys():
        builder.button(text=prod, callback_data=f"prot_{prod}")
    builder.button(text="➕ Свой продукт", callback_data="prot_custom")
    builder.button(text="⬅️ Отмена", callback_data="cancel_action")
    builder.adjust(1)
    
    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    await state.set_state(MealState.choosing_protein)
    await callback.answer()

# Выбор белка
@dp.callback_query(F.data.startswith("prot_"), MealState.choosing_protein)
async def process_protein(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.replace("prot_", "")
    if choice == "custom":
        await callback.message.answer("Напиши название своего белкового продукта и примерные КБЖУ через пробел (например: *Индейка 180г 200ккал 35б 5ж 0у*):", reply_markup=back_keyboard())
        await state.set_state(MealState.custom_product_input)
        await state.update_data(custom_type="protein")
        await callback.answer()
        return

    await state.update_data(selected_protein=choice)
    
    # Предлагаем углеводы
    builder = InlineKeyboardBuilder()
    for prod in CARBS.keys():
        builder.button(text=prod, callback_data=f"carb_{prod}")
    builder.button(text="➕ Свой углевод", callback_data="carb_custom")
    builder.button(text="⬅️ Назад", callback_data="back_to_prot")
    builder.adjust(1)
    
    await callback.message.edit_text(f"Белок: **{choice}** выбран ✅\nТеперь выбери гарнир / углеводы:")
    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    await state.set_state(MealState.choosing_carb)
    await callback.answer()

# Выбор углеводов
@dp.callback_query(F.data.startswith("carb_"), MealState.choosing_carb)
async def process_carb(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.replace("carb_", "")
    if choice == "custom":
        await callback.message.answer("Напиши свой гарнир и КБЖУ:", reply_markup=back_keyboard())
        await state.set_state(MealState.custom_product_input)
        await state.update_data(custom_type="carb")
        await callback.answer()
        return

    await state.update_data(selected_carb=choice)
    
    # Предлагаем жиры/овощи
    builder = InlineKeyboardBuilder()
    for prod in FATS_VEG.keys():
        builder.button(text=prod, callback_data=f"fat_{prod}")
    builder.button(text="➕ Свой продукт", callback_data="fat_custom")
    builder.button(text="⬅️ Назад", callback_data="back_to_carb")
    builder.adjust(1)
    
    await callback.message.edit_text(f"Гарнир: **{choice}** выбран ✅\nВыбери жиры или овощи:")
    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    await state.set_state(MealState.choosing_fat)
    await callback.answer()

# Выбор жиров/овощей и завершение приема пищи
@dp.callback_query(F.data.startswith("fat_"), MealState.choosing_fat)
async def process_fat(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.replace("fat_", "")
    if choice == "custom":
        await callback.message.answer("Напиши свой продукт и КБЖУ:", reply_markup=back_keyboard())
        await state.set_state(MealState.custom_product_input)
        await state.update_data(custom_type="fat")
        await callback.answer()
        return

    data = await state.get_data()
    p = PROTEINS.get(data["selected_protein"], {"cals": 200, "p": 35, "f": 5, "c": 0})
    c = CARBS.get(data["selected_carb"], {"cals": 250, "p": 6, "f": 2, "c": 50})
    f = FATS_VEG.get(choice, {"cals": 100, "p": 0, "f": 10, "c": 0})

    meal_cals = p["cals"] + c["cals"] + f["cals"]
    meal_p = p["p"] + c["p"] + f["p"]
    meal_f = p["f"] + c["f"] + f["f"]
    meal_c = p["c"] + c["c"] + f["c']" if "c'" in c else p["c"] + c["c"] + f["c"]

    meal_info = {
        "num": data["current_meal"],
        "items": [data["selected_protein"], data["selected_carb"], choice],
        "cals": meal_cals, "p": meal_p, "f": meal_f, "c": meal_c
    }

    meal_list = data.get("meal_data", [])
    meal_list.append(meal_info)
    await state.update_data(meal_data=meal_list)

    current_meal = data["current_meal"]
    
    response = (
        f"✅ **Прием пищи №{current_meal} готов!**\n"
        f"• {data['selected_protein']}\n"
        f"• {data['selected_carb']}\n"
        f"• {choice}\n\n"
        f"📊 **КБЖУ приема:** {meal_cals} ккал | Б: {meal_p}г | Ж: {meal_f}г | У: {meal_c}г\n"
    )

    if current_meal < 3:
        # Переходим к следующему приему пищи
        await state.update_data(current_meal=current_meal + 1)
        builder = InlineKeyboardBuilder()
        for prod in PROTEINS.keys():
            builder.button(text=prod, callback_data=f"prot_{prod}")
        builder.adjust(1)
        
        await callback.message.answer(response + f"\n👉 Переходим к **Приему пищи №{current_meal + 1}**. Выбери белок:", reply_markup=builder.as_markup())
        await state.set_state(MealState.choosing_protein)
    else:
        # Все 3 приема пищи собраны! Считаем итог за день
        total_cals = sum(m["cals"] for m in meal_list)
        total_p = sum(m["p"] for m in meal_list)
        total_f = sum(m["f"] for m in meal_list)
        total_c = sum(m["c"] for m in meal_list)

        user_id = callback.from_user.id
        if user_id not in user_history:
            user_history[user_id] = []
        user_history[user_id].append({"day_type": "Тренировка" if data["is_training"] else "Отдых", "cals": total_cals, "p": total_p, "f": total_f, "c": total_c})

        await callback.message.answer(
            response + "\n"
            "🎉 **Все 3 приема пищи успешно собраны!**\n"
            "════════════════════\n"
            f"🔥 **ИТОГ ЗА ДЕНЬ:**\n"
            f"Калории: **{total_cals} ккал**\n"
            f"Белки: **{total_p}г** | Жиры: **{total_f}г** | Углеводы: **{total_c}г**\n"
            "════════════════════\n"
            "💾 День сохранен в историю! Напиши команду **анализ**, чтобы посмотреть статистику за последние дни."
        )
        await state.clear()
    
    await callback.answer()

# Кнопка возврата / отмены
@dp.callback_query(F.data == "cancel_action")
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Действие отменено. Нажми /start, чтобы начать заново.")
    await callback.answer()

# Команда аналитики
@dp.message(F.text.lower().contains("анализ"))
async def show_analytics(message: types.Message):
    user_id = message.from_user.id
    history = user_history.get(user_id, [])
    
    if not history:
        await message.answer("У меня пока нет сохраненных дней. Собери хотя бы один день через /start!")
        return

    resp = "📈 **Твоя аналитика питания:**\n\n"
    for i, day in enumerate(history[-5:], 1): # Последние 5 дней
        resp += f"День {i} ({day['day_type']}): {day['cals']} ккал (Б:{day['p']} Ж:{day['f']} У:{day['c']})\n"
    
    await message.answer(resp)

# Веб-сервер для Render (поддержание порта)
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
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
