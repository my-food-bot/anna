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

user_history = {}

class MealState(StatesGroup):
    waiting_for_day_type = State()
    choosing_protein = State()
    choosing_carb = State()
    choosing_fat = State()
    waiting_for_analytics_period = State()

# Целевые значения на 1 прием пищи
TARGET_TRAIN = {"cals": 612, "p": 25, "f": 17, "c": 86}
TARGET_REST = {"cals": 436, "p": 17, "f": 12, "c": 61}

# Продукты для тренировочного дня (раздельно по позициям под цель)
PROTEINS_TRAIN = {
    "🥩 Куриная грудка (~250г)": TARGET_TRAIN,
    "🦃 Индейка (~250г)": TARGET_TRAIN,
    "🥩 Говядина (~200г)": TARGET_TRAIN,
    "🐟 Рыба / Лосось (~220г)": TARGET_TRAIN,
    "🐟 Тунец (консерв., ~180г)": TARGET_TRAIN,
    "🥤 Протеиновый изолят (1.5 мерн. ложки)": TARGET_TRAIN,
}

CARBS_TRAIN = {
    "🍚 Рис / Гречка (готовые, ~250г)": TARGET_TRAIN,
    "🍝 Макароны (готовые, ~250г)": TARGET_TRAIN,
    "🥔 Картофель отварной (~300г)": TARGET_TRAIN,
    "🍟 Картофель фри (аэрогриль, ~180г)": TARGET_TRAIN,
    "🥔 Пюре картофельное на молоке (~300г)": TARGET_TRAIN,
}

# Продукты для дня отдыха (раздельно по позициям под нижнюю норму)
PROTEINS_REST = {
    "🐟 Минтай (отварной/запеч., ~180г)": TARGET_REST,
    "🐟 Тунец (консерв., ~130г)": TARGET_REST,
    "🥚 Яйца (2 крупных шт.)": TARGET_REST,
    "🥛 Творог (~180г)": TARGET_REST,
    "🥩 Куриная грудка (~150г)": TARGET_REST,
    "🦃 Индейка (~150г)": TARGET_REST,
}

CARBS_REST = {
    "🥔 Запеченный бэби-картофель (аэрогриль, ~150г)": TARGET_REST,
    "🍞 Хлеб цельнозерновой (1 кусок)": TARGET_REST,
    "🍚 Рис / Гречка (готовые, ~130г)": TARGET_REST,
    "🍝 Макароны (готовые, ~130г)": TARGET_REST,
}

# Жиры и овощи (раздельно)
FATS_VEG = {
    "🫒 Оливковое масло (1 ч.л.)": {"cals": 0, "p": 0, "f": 0, "c": 0},
    "🥑 Авокадо (четвертинка, ~40г)": {"cals": 0, "p": 0, "f": 0, "c": 0},
    "🥜 Орехи (небольшая горсть, ~15г)": {"cals": 0, "p": 0, "f": 0, "c": 0},
    "🥗 Свежие овощи (миска салата)": {"cals": 0, "p": 0, "f": 0, "c": 0},
}

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Привет! Напиши слово **Меню**, чтобы собрать рацион на сегодня, "
        "или слово **анализ**, чтобы посмотреть статистику за прошлые дни."
    )

@dp.message(F.text.lower() == "меню")
async def cmd_menu(message: types.Message, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="🏋️ Тренировочный день (612 ккал/прием)", callback_data="day_train")
    builder.button(text="🛋️ День отдыха (436 ккал/прием)", callback_data="day_rest")
    builder.adjust(1)
    
    await message.answer(
        "🎯 Какой сегодня день?",
        reply_markup=builder.as_markup()
    )
    await state.set_state(MealState.waiting_for_day_type)

@dp.callback_query(MealState.waiting_for_day_type, F.data.in_({"day_train", "day_rest"}))
async def process_day_choice(callback: types.CallbackQuery, state: FSMContext):
    is_training = (callback.data == "day_train")
    target = TARGET_TRAIN if is_training else TARGET_REST
    await state.update_data(is_training=is_training, current_meal=1, meal_data=[], target=target)
    
    day_name = "Тренировочный день" if is_training else "День отдыха"
    await callback.answer(f"Выбран: {day_name}")
    
    proteins_pool = PROTEINS_TRAIN if is_training else PROTEINS_REST
    
    builder = InlineKeyboardBuilder()
    for prod in proteins_pool.keys():
        builder.button(text=prod, callback_data=f"prot_{prod}")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"⚡ Режим: **{day_name}**\n"
        f"🎯 Цель на 1 прием: Б: {target['p']}г | Ж: {target['f']}г | У: {target['c']}г ({target['cals']} ккал)\n\n"
        f"🍽️ Собираем **Прием пищи №1**.\nВыбери основной белок:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(MealState.choosing_protein)

@dp.callback_query(MealState.choosing_protein, F.data.startswith("prot_"))
async def process_protein(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.replace("prot_", "", 1)
    await state.update_data(selected_protein=choice)
    await callback.answer("Белок выбран")
    
    data = await state.get_data()
    carbs_pool = CARBS_TRAIN if data.get("is_training") else CARBS_REST
    
    builder = InlineKeyboardBuilder()
    for prod in carbs_pool.keys():
        builder.button(text=prod, callback_data=f"carb_{prod}")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"✅ Белок: {choice}\n\n🥔 Выбери гарнир / углеводы:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(MealState.choosing_carb)

@dp.callback_query(MealState.choosing_carb, F.data.startswith("carb_"))
async def process_carb(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.replace("carb_", "", 1)
    await state.update_data(selected_carb=choice)
    await callback.answer("Гарнир выбран")
    
    builder = InlineKeyboardBuilder()
    for prod in FATS_VEG.keys():
        builder.button(text=prod, callback_data=f"fat_{prod}")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"✅ Гарнир: {choice}\n\n🥗 Выбери жиры или овощи:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(MealState.choosing_fat)

@dp.callback_query(MealState.choosing_fat, F.data.startswith("fat_"))
async def process_fat(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.replace("fat_", "", 1)
    data = await state.get_data()
    await callback.answer("Прием учтен")
    
    target = data.get("target", TARGET_TRAIN)
    meal_cals = target["cals"]
    meal_p = target["p"]
    meal_f = target["f"]
    meal_uc = target["c"]

    # Проверка отклонений на КАЖДЫЙ прием пищи (±10%)
    target_meal_cals = target["cals"]
    lower_bound = target_meal_cals * 0.9
    upper_bound = target_meal_cals * 1.1

    meal_warning = ""
    if meal_cals > upper_bound:
        meal_warning = "\n⚠️ **Предупреждение:** Превышение нормы приема более чем на 10%!"
    elif meal_cals < lower_bound:
        meal_warning = "\n⚠️ **Предупреждение:** Недобор нормы приема более чем на 10%!"

    current_meal = data.get("current_meal", 1)
    meal_list = data.get("meal_data", [])
    meal_list.append({
        "num": current_meal,
        "cals": meal_cals, "p": meal_p, "f": meal_f, "c": meal_uc
    })
    await state.update_data(meal_data=meal_list)

    response = (
        f"✅ **Прием пищи №{current_meal} готов!**\n"
        f"• {data.get('selected_protein')}\n"
        f"• {data.get('selected_carb')}\n"
        f"• {choice}\n\n"
        f"📊 КБЖУ приема: {meal_cals} ккал | Б: {meal_p}г | Ж: {meal_f}г | У: {meal_uc}г"
        f"{meal_warning}\n"
    )

    if current_meal < 3:
        await state.update_data(current_meal=current_meal + 1)
        is_train = data.get("is_training")
        proteins_pool = PROTEINS_TRAIN if is_train else PROTEINS_REST
        builder = InlineKeyboardBuilder()
        for prod in proteins_pool.keys():
            builder.button(text=prod, callback_data=f"prot_{prod}")
        builder.button(text="❌ Отмена", callback_data="cancel_action")
        builder.adjust(1)
        
        await callback.message.answer(
            response + f"\n👉 Переходим к **Приему пищи №{current_meal + 1}**. Выбери белок:",
            reply_markup=builder.as_markup()
        )
        await state.set_state(MealState.choosing_protein)
    else:
        total_cals = sum(m["cals"] for m in meal_list)
        total_p = sum(m["p"] for m in meal_list)
        total_f = sum(m["f"] for m in meal_list)
        total_c = sum(m["c"] for m in meal_list)

        target_day_cals = target["cals"] * 3

        user_id = callback.from_user.id
        if user_id not in user_history:
            user_history[user_id] = []
        user_history[user_id].append({
            "day_type": "Тренировка" if data.get("is_training") else "Отдых",
            "cals": total_cals, "p": total_p, "f": total_f, "c": total_c
        })

        await callback.message.answer(
            response + "\n"
            "🎉 **Все 3 приема пищи собраны и сохранены!**\n"
            "════════════════════\n"
            f"🔥 **ИТОГ ЗА ДЕНЬ (Цель: ~{target_day_cals} ккал):**\n"
            f"Калории: **{total_cals} ккал**\n"
            f"Белки: **{total_p}г** | Жиры: **{total_f}г** | Углеводы: **{total_c}г**\n"
            "════════════════════\n"
            "Напиши **Меню**, чтобы собрать новый день, или **анализ** для статистики."
        )
        await state.clear()

@dp.message(F.text.lower() == "анализ")
async def cmd_analytics_request(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    history = user_history.get(user_id, [])
    if not history:
        await message.answer("⚠️ У тебя пока нет сохраненных дней. Сначала собери рацион через слово **Меню**!")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="3 дня", callback_data="period_3")
    builder.button(text="7 дней", callback_data="period_7")
    builder.button(text="Все сохраненные", callback_data="period_all")
    builder.adjust(1)

    await message.answer("📈 За какой период выдать аналитику?", reply_markup=builder.as_markup())
    await state.set_state(MealState.waiting_for_analytics_period)

@dp.callback_query(MealState.waiting_for_analytics_period, F.data.startswith("period_"))
async def process_analytics_period(callback: types.CallbackQuery, state: FSMContext):
    period_type = callback.data.replace("period_", "")
    user_id = callback.from_user.id
    history = user_history.get(user_id, [])
    
    await callback.answer("Аналитика сформирована")

    if period_type == "3":
        days_slice = history[-3:]
        title = "за последние 3 дня"
    elif period_type == "7":
        days_slice = history[-7:]
        title = "за последние 7 дней"
    else:
        days_slice = history
        title = "за все время"

    total_cals = sum(d["cals"] for d in days_slice)
    avg_cals = round(total_cals / len(days_slice)) if days_slice else 0

    resp = f"📊 **Аналитика питания ({title}):**\n\n"
    for i, day in enumerate(days_slice, 1):
        resp += f"• День {i} ({day['day_type']}): **{day['cals']} ккал** (Б:{day['p']} Ж:{day['f']} У:{day['c']})\n"
    
    resp += f"\n📉 Средняя калорийность: **{avg_cals} ккал/день**"
    await callback.message.edit_text(resp)
    await state.clear()

@dp.callback_query(F.data == "cancel_action")
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.answer("❌ Действие отменено. Напиши **Меню** или **анализ**.")

async def web_server_runner():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is alive!"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await web_server_runner()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
