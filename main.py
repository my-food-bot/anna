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
    choosing_protein_category = State()
    choosing_protein_item = State()
    choosing_carb = State()
    choosing_fat = State()
    waiting_for_analytics_period = State()

TARGET_TRAIN = {"cals": 612, "p": 25, "f": 17, "c": 86}
TARGET_REST = {"cals": 436, "p": 17, "f": 12, "c": 61}
ZERO_CARB = {"cals": 0, "p": 0, "f": 0, "c": 0}

PROTEIN_CATEGORIES = {
    "cat_fish": "🐟 Рыба и морепродукты",
    "cat_meat": "🥩 Мясо и птица",
    "cat_cheese": "🧀 Сыры",
    "cat_dairy_eggs": "🥛 Молочка и яйца",
    "cat_other": "🥤 Протеин / Изолят"
}

PROTEINS_TRAIN_BY_CAT = {
    "cat_fish": {
        "pt_5": ("🐟 Минтай (тушеный/запеченный) (~300г)", {"cals": 220, "p": 48, "f": 3, "c": 0}),
        "pt_6": ("🦐 Креветки отварные (~250г)", {"cals": 240, "p": 50, "f": 4, "c": 1}),
        "pt_7": ("🦑 Морской коктейль (~260г)", {"cals": 220, "p": 45, "f": 3, "c": 2}),
        "pt_8": ("🐟 Семга с/с (~180г)", {"cals": 360, "p": 36, "f": 24, "c": 0}),
        "pt_9": ("🐟 Скумбрия х/к (~160г)", {"cals": 350, "p": 32, "f": 25, "c": 0}),
        "pt_10": ("🐟 Тунец (консерв. в с/с) (~250г)", {"cals": 250, "p": 55, "f": 3, "c": 0}),
    },
    "cat_meat": {
        "pt_1": ("🥩 Куриная грудка / индейка запеч. (~250г)", {"cals": 275, "p": 55, "f": 5, "c": 0}),
        "pt_2": ("🍗 Куриные ножки (~220г)", {"cals": 350, "p": 40, "f": 20, "c": 0}),
        "pt_3": ("🍗 Куриное бедро (~200г)", {"cals": 360, "p": 38, "f": 22, "c": 0}),
        "pt_4": ("🥩 Свинина стейк (~180г)", {"cals": 380, "p": 36, "f": 25, "c": 0}),
        "pt_5": ("🍢 Свинина шашлык (~170г)", {"cals": 390, "p": 34, "f": 27, "c": 0}),
        "pt_6": ("🍲 Свинина тушеная (~180г)", {"cals": 370, "p": 35, "f": 24, "c": 0}),
        "pt_7": ("🥩 Говядина гуляш (~200г)", {"cals": 330, "p": 42, "f": 17, "c": 0}),
        "pt_8": ("🍖 Свиные ребра запеченные (~180г)", {"cals": 420, "p": 35, "f": 30, "c": 0}),
    },
    "cat_cheese": {
        "pt_13": ("🧀 Сыр Сулугуни (~100г)", {"cals": 290, "p": 20, "f": 22, "c": 0}),
        "pt_14": ("🧀 Сыр Пармезан (~80г)", {"cals": 320, "p": 28, "f": 22, "c": 0}),
        "pt_15": ("🧀 Сыр Российский / Голландский (~90г)", {"cals": 330, "p": 22, "f": 26, "c": 0}),
        "pt_16": ("🧀 Сыр Моцарелла (~110г)", {"cals": 280, "p": 20, "f": 20, "c": 2}),
        "pt_17": ("🧀 Творожный сыр (~150г)", {"cals": 330, "p": 9, "f": 32, "c": 4}),
    },
    "cat_dairy_eggs": {
        "pt_11": ("🥛 Творог 5% (~300г)", {"cals": 360, "p": 54, "f": 15, "c": 9}),
        "pt_12": ("🥚 Яйца вареные / жареные (4 шт.)", {"cals": 280, "p": 24, "f": 20, "c": 2}),
    },
    "cat_other": {
        "pt_18": ("🥤 Протеиновый изолят (2 мерн. ложки)", {"cals": 220, "p": 50, "f": 1, "c": 2}),
    }
}

PROTEINS_REST_BY_CAT = {
    "cat_fish": {
        "pr_1": ("🐟 Минтай (~220г)", {"cals": 160, "p": 35, "f": 2, "c": 0}),
        "pr_3": ("🦐 Креветки отварные (~180г)", {"cals": 170, "p": 36, "f": 3, "c": 1}),
        "pr_4": ("🦑 Морской коктейль (~190г)", {"cals": 160, "p": 32, "f": 2, "c": 1}),
        "pr_5": ("🐟 Семга с/с (~110г)", {"cals": 220, "p": 22, "f": 15, "c": 0}),
        "pr_6": ("🐟 Скумбрия х/к (~100г)", {"cals": 220, "p": 20, "f": 16, "c": 0}),
        "pr_7": ("🐟 Тунец (консерв.) (~180г)", {"cals": 180, "p": 40, "f": 2, "c": 0}),
    },
    "cat_meat": {
        "pr_2": ("🥩 Куриная грудка / индейка (~160г)", {"cals": 180, "p": 35, "f": 3, "c": 0}),
        "pr_3": ("🍗 Куриные ножки (~150г)", {"cals": 220, "p": 26, "f": 12, "c": 0}),
        "pr_4": ("🍗 Куриное бедро (~130г)", {"cals": 230, "p": 24, "f": 14, "c": 0}),
        "pr_5": ("🥩 Свинина стейк (~110г)", {"cals": 230, "p": 22, "f": 15, "c": 0}),
        "pr_6": ("🍲 Свинина тушеная (~110г)", {"cals": 220, "p": 21, "f": 14, "c": 0}),
        "pr_7": ("🥩 Говядина гуляш (~130г)", {"cals": 210, "p": 27, "f": 11, "c": 0}),
    },
    "cat_cheese": {
        "pr_10": ("🧀 Сыр Сулугуни (~70г)", {"cals": 200, "p": 14, "f": 15, "c": 0}),
        "pr_11": ("🧀 Сыр Пармезан (~55г)", {"cals": 220, "p": 19, "f": 15, "c": 0}),
        "pr_12": ("🧀 Сыр Российский / Голландский (~60г)", {"cals": 220, "p": 15, "f": 17, "c": 0}),
        "pr_13": ("🧀 Сыр Моцарелла (~75г)", {"cals": 190, "p": 14, "f": 14, "c": 1}),
        "pr_14": ("🧀 Творожный сыр (~100г)", {"cals": 220, "p": 6, "f": 21, "c": 3}),
    },
    "cat_dairy_eggs": {
        "pr_8": ("🥛 Творог 5% (~200г)", {"cals": 240, "p": 36, "f": 10, "c": 6}),
        "pr_9": ("🥚 Яйца вареные / жареные (3 шт.)", {"cals": 210, "p": 18, "f": 15, "c": 1}),
    },
    "cat_other": {
        "pr_15": ("🥤 Протеиновый изолят (1 мерн. ложка)", {"cals": 110, "p": 25, "f": 0, "c": 1}),
    }
}

CARBS_TRAIN = {
    "ct_1": ("🍚 Гречка / Рис (~300г)", TARGET_TRAIN),
    "ct_2": ("🍝 Макароны (~280г)", TARGET_TRAIN),
    "ct_3": ("🍞 Черный хлеб (~140г)", TARGET_TRAIN),
    "ct_4": ("🍞 Хлеб бородинский (~140г)", TARGET_TRAIN),
    "ct_5": ("🫓 Тонкий лаваш (~130г)", TARGET_TRAIN),
    "ct_6": ("🍲 Овощной суп / Борщ (~500г)", TARGET_TRAIN),
    "ct_7": ("🍜 Суп Том Ям (~450г)", TARGET_TRAIN),
}

CARBS_REST = {
    "cr_1": ("🍚 Гречка / Рис (~180г)", TARGET_REST),
    "cr_2": ("🍝 Макароны (~170г)", TARGET_REST),
    "cr_3": ("🍞 Черный хлеб (~70г)", TARGET_REST),
    "cr_4": ("🍞 Хлеб бородинский (~70г)", TARGET_REST),
    "cr_5": ("🫓 Тонкий лаваш (~70г)", TARGET_REST),
    "cr_6": ("🍲 Овощной суп / Борщ (~350г)", TARGET_REST),
}

FATS_VEG = {
    "f_1": ("🥗 Овощной салат", {"cals": 40, "p": 1, "f": 3, "c": 4}),
    "f_2": ("🥬 Капуста квашеная", {"cals": 25, "p": 1, "f": 0, "c": 4}),
    "f_3": ("🥗 Капуста «фитнес» без сахара", {"cals": 30, "p": 1, "f": 0, "c": 5}),
    "f_4": ("🍠 Вареная свекла (~100г)", {"cals": 45, "p": 1, "f": 0, "c": 10}),
    "f_5": ("🥕 Морковь свежая тертая (~100г)", {"cals": 35, "p": 1, "f": 0, "c": 8}),
    "f_6": ("🥬 Капуста пекинская (~150г)", {"cals": 25, "p": 2, "f": 0, "c": 4}),
    "f_7": ("🥒 Огурцы (~200г)", {"cals": 30, "p": 1, "f": 0, "c": 6}),
    "f_8": ("🍅 Помидоры черри (~150г)", {"cals": 30, "p": 1, "f": 0, "c": 6}),
    "f_9": ("🥑 Авокадо (~50г)", {"cals": 80, "p": 1, "f": 7, "c": 2}),
    "f_10": ("🧈 Сливочное масло (10г)", {"cals": 75, "p": 0, "f": 8, "c": 0}),
    "f_11": ("🫒 Оливковое масло (1 ч.л.)", {"cals": 45, "p": 0, "f": 5, "c": 0}),
    "f_12": ("🥜 Орехи (~15г)", {"cals": 100, "p": 3, "f": 9, "c": 3}),
    "f_13": ("🌱 Семена чиа / Псиллиум", {"cals": 50, "p": 2, "f": 3, "c": 4}),
    "f_14": ("🥛 Кефир 1% (250 мл)", {"cals": 100, "p": 7, "f": 2, "c": 10}),
}

MEAL_NAMES = {1: "Завтрак", 2: "Обед", 3: "Ужин"}

def format_diff(val, target):
    diff = val - target
    sign = "+" if diff > 0 else ""
    return f"{val} ({sign}{diff})"

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
    builder.button(text="🏋️ Тренировочный день", callback_data="day_train")
    builder.button(text="🛋️ День отдыха", callback_data="day_rest")
    builder.adjust(1)
    
    await message.answer("🎯 Какой сегодня день?", reply_markup=builder.as_markup())
    await state.set_state(MealState.waiting_for_day_type)

@dp.callback_query(MealState.waiting_for_day_type, F.data.in_({"day_train", "day_rest"}))
async def process_day_choice(callback: types.CallbackQuery, state: FSMContext):
    is_training = (callback.data == "day_train")
    target = TARGET_TRAIN if is_training else TARGET_REST
    await state.update_data(
        is_training=is_training, 
        current_meal=1, 
        meal_data=[], 
        target=target,
        current_meal_items=[],
        current_meal_cals=0,
        current_meal_p=0,
        current_meal_f=0,
        current_meal_c=0
    )
    
    day_name = "Тренировочный день" if is_training else "День отдыха"
    await callback.answer(f"Выбран: {day_name}")
    await show_protein_categories(callback.message, state, edit=True)

async def show_protein_categories(message: types.Message, state: FSMContext, edit=False):
    data = await state.get_data()
    current_meal = data.get("current_meal", 1)
    meal_title = MEAL_NAMES.get(current_meal, "Прием пищи")
    
    builder = InlineKeyboardBuilder()
    for cat_code, cat_name in PROTEIN_CATEGORIES.items():
        builder.button(text=cat_name, callback_data=f"protcat_{cat_code}")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(1)
    
    text = f"🍽️ Собираем **{meal_title}**.\nВыбери категорию белка:"
    if edit:
        await message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await message.answer(text, reply_markup=builder.as_markup())
    await state.set_state(MealState.choosing_protein_category)

@dp.callback_query(MealState.choosing_protein_category, F.data.startswith("protcat_"))
async def process_protein_category(callback: types.CallbackQuery, state: FSMContext):
    cat_code = callback.data.replace("protcat_", "", 1)
    data = await state.get_data()
    is_train = data.get("is_training")
    
    pool_by_cat = PROTEINS_TRAIN_BY_CAT if is_train else PROTEINS_REST_BY_CAT
    items = pool_by_cat.get(cat_code, {})
    
    if not items:
        await callback.answer("В этой категории пока пусто", show_alert=True)
        return

    await callback.answer()
    selected_items = data.get("current_meal_items", [])

    builder = InlineKeyboardBuilder()
    for item_code, (item_name, _) in items.items():
        mark = "✅ " if item_code in selected_items else ""
        builder.button(text=f"{mark}{item_name}", callback_data=f"protitem_{item_code}")
    builder.button(text="➡️ Далее (к гарнирам)", callback_data="proceed_to_carbs")
    builder.button(text="⬅️ Назад к категориям", callback_data="back_to_prot_cats")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "🥩 Выбери продукты (можно несколько) и нажми **«➡️ Далее»**:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(MealState.choosing_protein_item)

@dp.callback_query(F.data == "back_to_prot_cats")
async def back_to_protein_categories(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await show_protein_categories(callback.message, state, edit=True)

@dp.callback_query(MealState.choosing_protein_item, F.data.startswith("protitem_"))
async def toggle_protein_item(callback: types.CallbackQuery, state: FSMContext):
    code = callback.data.replace("protitem_", "", 1)
    data = await state.get_data()
    is_train = data.get("is_training")
    
    pool_by_cat = PROTEINS_TRAIN_BY_CAT if is_train else PROTEINS_REST_BY_CAT
    
    found_item = None
    found_cat = None
    for cat_code, items in pool_by_cat.items():
        if code in items:
            found_item = items[code]
            found_cat = cat_code
            break
            
    if not found_item:
        await callback.answer("Ошибка выбора", show_alert=True)
        return

    selected_items = data.get("current_meal_items", [])
    if code in selected_items:
        selected_items.remove(code)
        await callback.answer("Убрано из выбора")
    else:
        selected_items.append(code)
        await callback.answer("Добавлено")

    await state.update_data(current_meal_items=selected_items)
    
    items = pool_by_cat.get(found_cat, {})
    builder = InlineKeyboardBuilder()
    for item_code, (item_name, _) in items.items():
        mark = "✅ " if item_code in selected_items else ""
        builder.button(text=f"{mark}{item_name}", callback_data=f"protitem_{item_code}")
    builder.button(text="➡️ Далее (к гарнирам)", callback_data="proceed_to_carbs")
    builder.button(text="⬅️ Назад к категориям", callback_data="back_to_prot_cats")
    builder.adjust(1)
    
    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())

@dp.callback_query(MealState.choosing_protein_item, F.data == "proceed_to_carbs")
async def proceed_to_carbs(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    is_train = data.get("is_training")
    
    carbs_pool = CARBS_TRAIN if is_train else CARBS_REST
    
    builder = InlineKeyboardBuilder()
    for c_code, (c_name, _) in carbs_pool.items():
        builder.button(text=c_name, callback_data=f"carb_{c_code}")
    builder.button(text="⏭️ Пропустить углеводы", callback_data="carb_skip_carb")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "🥔 Выбери гарнир / углеводы (или пропусти):",
        reply_markup=builder.as_markup()
    )
    await state.set_state(MealState.choosing_carb)

@dp.callback_query(MealState.choosing_carb, F.data.startswith("carb_"))
async def process_carb(callback: types.CallbackQuery, state: FSMContext):
    code = callback.data.replace("carb_", "", 1)
    data = await state.get_data()
    is_train = data.get("is_training")
    
    if code == "skip_carb":
        carb_name = "Без углеводов (пропущено)"
        carb_vals = ZERO_CARB
    else:
        carbs_pool = CARBS_TRAIN if is_train else CARBS_REST
        if code not in carbs_pool:
            await callback.answer("Ошибка выбора", show_alert=True)
            return
        carb_name, carb_vals = carbs_pool[code]
        
    await state.update_data(selected_carb=carb_name, carb_vals=carb_vals)
    await callback.answer("Углеводы учтены")
    
    builder = InlineKeyboardBuilder()
    for f_code, (f_name, _) in FATS_VEG.items():
        builder.button(text=f_name, callback_data=f"fat_{f_code}")
    builder.button(text="⏭️ Пропустить жиры/овощи", callback_data="fat_skip_fat")
    builder.button(text="❌ Отмена", callback_data="cancel_action")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "🥗 Выбери жиры, овощи или добавки (или пропусти):",
        reply_markup=builder.as_markup()
    )
    await state.set_state(MealState.choosing_fat)

@dp.callback_query(MealState.choosing_fat, F.data.startswith("fat_"))
async def process_fat(callback: types.CallbackQuery, state: FSMContext):
    code = callback.data.replace("fat_", "", 1)
    data = await state.get_data()
    
    if code == "skip_fat":
        fat_name = "Без жиров/овощей"
        fat_vals = ZERO_CARB
    else:
        if code not in FATS_VEG:
            await callback.answer("Ошибка выбора", show_alert=True)
            return
        fat_name, fat_vals = FATS_VEG[code]
        
    await callback.answer("Прием учтен")
    
    is_train = data.get("is_training")
    pool_by_cat = PROTEINS_TRAIN_BY_CAT if is_train else PROTEINS_REST_BY_CAT
    selected_item_codes = data.get("current_meal_items", [])
    
    total_p_cals, total_p_p, total_p_f, total_p_c = 0, 0, 0, 0
    protein_names_list = []
    
    for code_item in selected_item_codes:
        for cat_code, items in pool_by_cat.items():
            if code_item in items:
                p_name, p_val = items[code_item]
                protein_names_list.append(p_name)
                total_p_cals += p_val["cals"]
                total_p_p += p_val["p"]
                total_p_f += p_val["f"]
                total_p_c += p_val["c"]

    if not protein_names_list:
        protein_names_list = ["Белки не выбраны"]

    c_vals = data.get("carb_vals", ZERO_CARB)
    
    meal_cals = total_p_cals + c_vals["cals"] + fat_vals["cals"]
    meal_p = total_p_p + c_vals["p"] + fat_vals["p"]
    meal_f = total_p_f + c_vals["f"] + fat_vals["f"]
    meal_uc = total_p_c + c_vals["c"] + fat_vals["c"]

    target = data.get("target", TARGET_TRAIN)
    target_meal_cals = target["cals"]
    lower_bound = target_meal_cals * 0.9
    upper_bound = target_meal_cals * 1.1

    current_meal = data.get("current_meal", 1)
    meal_title = MEAL_NAMES.get(current_meal, "Прием пищи")
    
    meal_list = data.get("meal_data", [])
    meal_list.append({
        "num": current_meal,
        "name": meal_title,
        "cals": meal_cals, "p": meal_p, "f": meal_f, "c": meal_uc
    })
    await state.update_data(meal_data=meal_list)

    proteins_str = "\n• ".join(protein_names_list)
    
    # Форматируем вывод с отклонениями (в скобках)
    cals_str = format_diff(meal_cals, target["cals"])
    p_str = format_diff(meal_p, target["p"])
    f_str = format_diff(meal_f, target["f"])
    c_str = format_diff(meal_uc, target["c"])

    response = (
        f"✅ **{meal_title} готов!**\n"
        f"• {proteins_str}\n"
        f"• {data.get('selected_carb')}\n"
        f"• {fat_name}\n\n"
        f"📊 КБЖУ приема:\n"
        f"• Калории: **{cals_str}** ккал\n"
        f"• Белки: **{p_str}** г\n"
        f"• Жиры: **{f_str}** г\n"
        f"• Углеводы: **{c_str}** г\n"
    )

    if meal_cals < lower_bound:
        response += "\n⚠️ **Внимание:** Калорийность приема ниже целевой нормы более чем на 10%!"
        
        if current_meal < 3:
            builder = InlineKeyboardBuilder()
            builder.button(text="➕ Добавить еще категорию", callback_data="add_more_category")
            builder.button(text="➡️ Перейти к следующему приему", callback_data="next_meal_force")
            builder.adjust(1)
            
            await callback.message.answer(response + "\nХотите добавить что-то еще?", reply_markup=builder.as_markup())
            return
    
    await proceed_to_next_meal(callback.message, state, response)

@dp.callback_query(F.data == "add_more_category")
async def add_more_category(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(current_meal_items=[])
    await show_protein_categories(callback.message, state, edit=False)

@dp.callback_query(F.data == "next_meal_force")
async def next_meal_force(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await proceed_to_next_meal(callback.message, state, "")

async def proceed_to_next_meal(message: types.Message, state: FSMContext, prev_response: str):
    data = await state.get_data()
    current_meal = data.get("current_meal", 1)
    
    if current_meal < 3:
        next_meal_num = current_meal + 1
        await state.update_data(current_meal=next_meal_num, current_meal_items=[])
        next_title = MEAL_NAMES.get(next_meal_num, "Следующий прием")
        
        builder = InlineKeyboardBuilder()
        for cat_code, cat_name in PROTEIN_CATEGORIES.items():
            builder.button(text=cat_name, callback_data=f"protcat_{cat_code}")
        builder.button(text="❌ Отмена", callback_data="cancel_action")
        builder.adjust(1)
        
        await message.answer(
            prev_response + f"\n👉 Переходим к **{next_title}**. Выбери категорию белка:",
            reply_markup=builder.as_markup()
        )
        await state.set_state(MealState.choosing_protein_category)
    else:
        meal_list = data.get("meal_data", [])
        total_cals = sum(m["cals"] for m in meal_list)
        total_p = sum(m["p"] for m in meal_list)
        total_f = sum(m["f"] for m in meal_list)
        total_c = sum(m["c"] for m in meal_list)

        target = data.get("target", TARGET_TRAIN)
        target_day_cals = target["cals"] * 3
        target_day_p = target["p"] * 3
        target_day_f = target["f"] * 3
        target_day_c = target["c"] * 3

        day_cals_str = format_diff(total_cals, target_day_cals)
        day_p_str = format_diff(total_p, target_day_p)
        day_f_str = format_diff(total_f, target_day_f)
        day_c_str = format_diff(total_c, target_day_c)

        user_id = message.chat.id
        if user_id not in user_history:
            user_history[user_id] = []
        user_history[user_id].append({
            "day_type": "Тренировка" if data.get("is_training") else "Отдых",
            "cals": total_cals, "p": total_p, "f": total_f, "c": total_c
        })

        await message.answer(
            prev_response + "\n"
            "🎉 **Все 3 приема пищи (Завтрак, Обед, Ужин) собраны и сохранены!**\n"
            "════════════════════\n"
            f"🔥 **ИТОГ ЗА ДЕНЬ:**\n"
            f"• Калории: **{day_cals_str}** ккал\n"
            f"• Белки: **{day_p_str}** г\n"
            f"• Жиры: **{day_f_str}** г\n"
            f"• Углеводы: **{day_c_str}** г\n"
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
async def cancel_handler(
