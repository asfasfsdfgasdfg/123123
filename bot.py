import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.client.session.aiohttp import AiohttpSession
from datetime import datetime
import time
import json
import os

session = AiohttpSession(timeout=300)

TOKEN = "8953142991:AAEH2bhrfROc8358a0dseSh5Hb04gPS0Xf4"
YOUR_TELEGRAM_ID = 1795960713

# ===== СПИСОК АДМИНИСТРАТОРОВ =====
ADMINS = {YOUR_TELEGRAM_ID}
ADMIN_NAMES = {}

# ===== ДАННЫЕ =====
PRODUCTS = {
    "Товар 1": {"price": "100 руб.", "desc": "Описание товара 1", "photo": "421.png"},
    "Товар 2": {"price": "200 руб.", "desc": "Описание товара 2", "photo": "321.png"},
    "Товар 3": {"price": "300 руб.", "desc": "Описание товара 3", "photo": "123.jpg"},
}

ANTISPAM_SETTINGS = {
    "min_time_between_orders": 30,
    "max_orders_per_day": 5,
}

bot = Bot(token=TOKEN, session=session)
dp = Dispatcher()

# ===== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =====
user_orders = {}
sales_paused = False
total_orders_all_time = 0
product_stats = {}
user_order_history = {}
users_list = set()
TEMP_DATA = {}


# ===== ФУНКЦИЯ ДЛЯ ДОБАВЛЕНИЯ ПОЛЬЗОВАТЕЛЕЙ =====
def add_user(user_id: int):
    if user_id not in users_list:
        users_list.add(user_id)
        print(f"👤 Добавлен новый пользователь: {user_id}")


# ===== ФУНКЦИИ =====
def is_admin(user_id: int) -> bool:
    return user_id in ADMINS


def get_admin_name(user_id: int) -> str:
    if user_id in ADMIN_NAMES:
        return ADMIN_NAMES[user_id]
    try:
        user = bot.get_chat(user_id)
        if user.username:
            return f"@{user.username}"
        else:
            return user.first_name
    except:
        return str(user_id)


def get_user_order_data(user_id: int):
    today = datetime.now().day
    if user_id not in user_orders:
        user_orders[user_id] = {
            "last_order_time": 0,
            "daily_orders": 0,
            "last_reset_day": today
        }
        return user_orders[user_id]
    if user_orders[user_id]["last_reset_day"] != today:
        user_orders[user_id]["daily_orders"] = 0
        user_orders[user_id]["last_reset_day"] = today
    return user_orders[user_id]


def check_order_limit(user_id: int) -> tuple[bool, str]:
    data = get_user_order_data(user_id)
    current_time = time.time()
    time_since_last = current_time - data["last_order_time"]
    if time_since_last < ANTISPAM_SETTINGS["min_time_between_orders"]:
        wait_time = int(ANTISPAM_SETTINGS["min_time_between_orders"] - time_since_last)
        return False, f"⏳ Пожалуйста, подождите {wait_time} секунд перед следующим заказом."
    if data["daily_orders"] >= ANTISPAM_SETTINGS["max_orders_per_day"]:
        return False, f"❌ Вы исчерпали лимит заказов на сегодня. Попробуйте завтра."
    return True, ""


def update_user_order(user_id: int, product_name: str):
    global total_orders_all_time

    data = get_user_order_data(user_id)
    data["last_order_time"] = time.time()
    data["daily_orders"] += 1
    total_orders_all_time += 1

    if product_name not in product_stats:
        product_stats[product_name] = 0
    product_stats[product_name] += 1

    if user_id not in user_order_history:
        user_order_history[user_id] = []
    user_order_history[user_id].append({
        "product": product_name,
        "time": time.time(),
        "date": datetime.now().strftime("%d.%m.%Y %H:%M")
    })
    add_user(user_id)


def catalog_button():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Каталог", callback_data="catalog")]]
    )


def product_buttons():
    buttons = []
    for name in PRODUCTS.keys():
        buttons.append(InlineKeyboardButton(text=name, callback_data=f"product_{name}"))
    keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def order_button(product_name):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оформить заказ", callback_data=f"order_{product_name}")]
        ]
    )


# ===== КОМАНДЫ АДМИНИСТРАТОРА =====

@dp.message(Command("start"))
async def start(message: types.Message):
    add_user(message.from_user.id)

    if is_admin(message.from_user.id):
        status_text = "🔴 Продажи приостановлены" if sales_paused else "🟢 Продажи активны"
        admin_name = get_admin_name(message.from_user.id)

        admins_list = []
        for admin_id in ADMINS:
            name = get_admin_name(admin_id)
            admins_list.append(f"👤 {name} (`{admin_id}`)")
        admins_text = "\n".join(admins_list)

        await message.answer(
            f"👋 **Здравствуйте, {admin_name}!**\n\n"
            f"📊 Текущий статус: {status_text}\n"
            f"📦 Всего заказов: {total_orders_all_time}\n"
            f"👥 Пользователей: {len(users_list)}\n\n"
            f"👑 **Администраторы:**\n{admins_text}\n\n"
            f"🔧 **Доступные команды:**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 `/pause` - Приостановить продажи\n"
            f"📌 `/resume` - Возобновить продажи\n"
            f"📌 `/status` - Полная статистика\n"
            f"📌 `/reset_daily` - Сброс ежедневной статистики\n"
            f"📌 `/reset_all` - Полный сброс ВСЕЙ статистики\n"
            f"📌 `/add_admin ID` - Добавить администратора\n"
            f"📌 `/remove_admin ID` - Удалить администратора\n"
            f"📌 `/admins` - Список администраторов\n"
            f"📌 `/setname Имя` - Установить своё имя\n"
            f"📌 `/add_product` - Добавить новый товар\n"
            f"📌 `/broadcast Текст` - Рассылка всем пользователям\n"
            f"📌 `/users_count` - Количество пользователей\n"
            f"📌 `/test Текст` - Тестовая рассылка\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Для просмотра каталога нажмите кнопку ниже:",
            reply_markup=catalog_button(),
            parse_mode="Markdown"
        )
    else:
        status_text = "🔴 Продажи приостановлены" if sales_paused else "🟢 Продажи активны"
        await message.answer(
            f"{status_text}\n\nНажмите кнопку ниже чтобы посмотреть каталог:",
            reply_markup=catalog_button()
        )


@dp.message(Command("users_count"))
async def show_users_count(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    users_list_str = "\n".join([f"• {uid}" for uid in list(users_list)[:20]])
    total = len(users_list)

    await message.answer(
        f"👥 **СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ:**\n\n"
        f"Всего пользователей: **{total}**\n\n"
        f"Последние 20 пользователей:\n"
        f"{users_list_str if users_list_str else 'Нет пользователей'}"
        f"\n\n{'... и еще ' + str(total - 20) if total > 20 else ''}"
    )


@dp.message(Command("test"))
async def test_broadcast(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        await message.answer(
            "🧪 **Тестовая рассылка**\n\n"
            "Используйте: `/test Текст для теста`\n\n"
            "Это отправит сообщение только вам для проверки."
        )
        return

    await message.answer(
        f"🧪 **ТЕСТОВОЕ СООБЩЕНИЕ**\n\n"
        f"✅ Рассылка работает!\n\n"
        f"Ваше сообщение:\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{args[1]}\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"Всего пользователей в базе: {len(users_list)}"
    )


@dp.message(Command("status"))
async def sales_status(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    status = "🔴 ПРИОСТАНОВЛЕНЫ" if sales_paused else "🟢 АКТИВНЫ"
    users_count = len(users_list)
    daily_orders = sum(data["daily_orders"] for data in user_orders.values())

    product_stats_text = ""
    if product_stats:
        sorted_products = sorted(product_stats.items(), key=lambda x: x[1], reverse=True)
        for i, (name, count) in enumerate(sorted_products, 1):
            product_stats_text += f"{i}. {name}: {count} заказов\n"
    else:
        product_stats_text = "Заказов пока нет"

    history_text = ""
    all_orders = []
    for user_id, orders in user_order_history.items():
        for order in orders:
            all_orders.append((order["date"], user_id, order["product"]))

    all_orders.sort(key=lambda x: x[0], reverse=True)
    recent_orders = all_orders[:10]

    if recent_orders:
        history_text = "📋 **Последние заказы:**\n"
        for date, user_id, product in recent_orders:
            history_text += f"• {date} - {product} (ID: {user_id})\n"
    else:
        history_text = "Заказов пока нет"

    await message.answer(
        f"📊 **СТАТИСТИКА ПРОДАЖ:**\n\n"
        f"📌 Статус: {status}\n"
        f"👥 Пользователей: {users_count}\n"
        f"📦 Заказов сегодня: {daily_orders}\n"
        f"🏆 Заказов за все время: {total_orders_all_time}\n\n"
        f"📈 **Статистика по товарам:**\n{product_stats_text}\n\n"
        f"{history_text}"
    )


@dp.message(Command("add_product"))
async def add_product_start(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    TEMP_DATA[message.from_user.id] = {}
    await message.answer(
        "🛍 **Добавление нового товара**\n\n"
        "Введите название товара:\n"
        "(Отправьте 'отмена' чтобы отменить)"
    )


@dp.message()
async def handle_add_product_steps(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    user_id = message.from_user.id
    if user_id not in TEMP_DATA:
        return

    if message.text.lower() == "отмена":
        del TEMP_DATA[user_id]
        await message.answer("❌ Добавление товара отменено.")
        return

    data = TEMP_DATA[user_id]

    if "name" not in data:
        data["name"] = message.text
        await message.answer(
            f"✅ Название: {data['name']}\n\n"
            "Введите цену товара (например: 500 руб.):"
        )
    elif "price" not in data:
        data["price"] = message.text
        await message.answer(
            f"✅ Название: {data['name']}\n"
            f"✅ Цена: {data['price']}\n\n"
            "Введите описание товара:"
        )
    elif "desc" not in data:
        data["desc"] = message.text
        await message.answer(
            f"✅ Название: {data['name']}\n"
            f"✅ Цена: {data['price']}\n"
            f"✅ Описание: {data['desc']}\n\n"
            "📎 Отправьте фото товара (или отправьте 'пропустить'):"
        )
    elif "photo" not in data:
        if message.text.lower() == "пропустить":
            data["photo"] = None
        elif message.photo:
            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)
            file_path = f"images/{data['name']}_{int(time.time())}.jpg"
            await bot.download_file(file.file_path, file_path)
            data["photo"] = file_path
        else:
            await message.answer("❌ Отправьте фото или напишите 'пропустить':")
            return

        PRODUCTS[data["name"]] = {
            "price": data["price"],
            "desc": data["desc"],
            "photo": data["photo"] if data["photo"] else "default.jpg"
        }

        del TEMP_DATA[user_id]
        await message.answer(
            f"✅ **Товар успешно добавлен!**\n\n"
            f"📌 {data['name']}\n"
            f"💰 {data['price']}\n"
            f"📝 {data['desc']}\n\n"
            f"Теперь товар доступен в каталоге.",
            parse_mode="Markdown"
        )


@dp.message(Command("broadcast"))
async def broadcast_message(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        await message.answer(
            "❌ Неправильный формат!\n\n"
            "Используйте: `/broadcast Текст для рассылки`\n"
            "Например: `/broadcast Внимание! Сегодня скидка 20%!`\n\n"
            f"👥 Пользователей в базе: {len(users_list)}"
        )
        return

    if len(users_list) == 0:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Всё равно отправить", callback_data="confirm_broadcast")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast")]
            ]
        )
        await message.answer(
            f"⚠️ **ВНИМАНИЕ!**\n\n"
            f"В базе **нет пользователей** для рассылки.\n\n"
            f"Чтобы добавить пользователей:\n"
            f"• Пользователи должны написать боту команду /start\n"
            f"• Или оформить заказ\n\n"
            f"Хотите отправить тестовое сообщение?",
            reply_markup=keyboard
        )
        TEMP_DATA[f"broadcast_{message.from_user.id}"] = args[1]
        return

    broadcast_text = args[1]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_broadcast"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast")
            ]
        ]
    )

    await message.answer(
        f"📨 **Подтверждение рассылки**\n\n"
        f"Будет отправлено **{len(users_list)}** пользователям.\n\n"
        f"Текст сообщения:\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{broadcast_text}\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"Подтвердите отправку:",
        reply_markup=keyboard
    )

    TEMP_DATA[f"broadcast_{message.from_user.id}"] = broadcast_text


@dp.callback_query(lambda c: c.data == "confirm_broadcast")
async def confirm_broadcast(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    key = f"broadcast_{callback.from_user.id}"
    if key not in TEMP_DATA:
        await callback.answer("❌ Нет текста для рассылки.", show_alert=True)
        return

    broadcast_text = TEMP_DATA[key]
    del TEMP_DATA[key]

    await callback.message.edit_text("⏳ Идет отправка сообщений...")

    total_users = len(users_list)
    success_count = 0
    fail_count = 0
    failed_users = []

    for i, user_id in enumerate(users_list):
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"📢 **Объявление от администрации**\n\n{broadcast_text}",
                parse_mode="Markdown"
            )
            success_count += 1

            if i % 10 == 0:
                await callback.message.edit_text(
                    f"⏳ Отправка сообщений... {i}/{total_users}\n"
                    f"✅ Успешно: {success_count}\n"
                    f"❌ Ошибок: {fail_count}"
                )

            await asyncio.sleep(0.05)
        except Exception as e:
            fail_count += 1
            failed_users.append(user_id)
            print(f"❌ Ошибка отправки пользователю {user_id}: {e}")

    result_text = (
        f"✅ **Рассылка завершена!**\n\n"
        f"📊 Результаты:\n"
        f"✅ Успешно отправлено: **{success_count}**\n"
        f"❌ Ошибок доставки: **{fail_count}**\n"
        f"👥 Всего пользователей: **{total_users}**\n"
    )

    if failed_users:
        result_text += f"\n⚠️ Не доставлено пользователям:\n{', '.join(map(str, failed_users[:10]))}"
        if len(failed_users) > 10:
            result_text += f"\n... и еще {len(failed_users) - 10}"

    await callback.message.edit_text(result_text)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "cancel_broadcast")
async def cancel_broadcast(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    key = f"broadcast_{callback.from_user.id}"
    if key in TEMP_DATA:
        del TEMP_DATA[key]

    await callback.message.edit_text("❌ Рассылка отменена.")
    await callback.answer()


@dp.message(Command("setname"))
async def set_admin_name(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        await message.answer(
            "❌ Неправильный формат!\n\n"
            "Используйте: `/setname Ваше имя`\n"
            "Например: `/setname Алексей`"
        )
        return

    new_name = args[1].strip()
    if len(new_name) > 50:
        await message.answer("❌ Имя не может быть длиннее 50 символов.")
        return

    ADMIN_NAMES[message.from_user.id] = new_name
    await message.answer(
        f"✅ Ваше имя успешно установлено!\n\n"
        f"Теперь приветствие: **Здравствуйте, {new_name}!**",
        parse_mode="Markdown"
    )


@dp.message(Command("admins"))
async def show_admins(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    admins_list = []
    for admin_id in ADMINS:
        name = get_admin_name(admin_id)
        if admin_id == YOUR_TELEGRAM_ID:
            admins_list.append(f"⭐ {name} (`{admin_id}`) - Главный администратор")
        else:
            admins_list.append(f"👤 {name} (`{admin_id}`)")

    admins_text = "\n".join(admins_list)
    await message.answer(
        f"👑 **Список администраторов:**\n\n"
        f"{admins_text}\n\n"
        f"Всего: {len(ADMINS)} администраторов",
        parse_mode="Markdown"
    )


@dp.message(Command("add_admin"))
async def add_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer(
            "❌ Неправильный формат!\n\n"
            "Используйте: `/add_admin 123456789`"
        )
        return

    try:
        new_admin_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
        return

    if new_admin_id in ADMINS:
        await message.answer(f"❌ Пользователь с ID `{new_admin_id}` уже является администратором.",
                             parse_mode="Markdown")
        return

    ADMINS.add(new_admin_id)
    await message.answer(
        f"✅ Администратор с ID `{new_admin_id}` успешно добавлен!",
        parse_mode="Markdown"
    )

    try:
        new_admin_name = get_admin_name(new_admin_id)
        await bot.send_message(
            chat_id=new_admin_id,
            text=f"🎉 **Поздравляю, {new_admin_name}! Вы стали администратором бота!**\n\n"
                 f"Используйте `/start` для просмотра всех команд.",
            parse_mode="Markdown"
        )
    except:
        pass


@dp.message(Command("remove_admin"))
async def remove_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer(
            "❌ Неправильный формат!\n\n"
            "Используйте: `/remove_admin 123456789`"
        )
        return

    try:
        admin_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
        return

    if admin_id == YOUR_TELEGRAM_ID:
        await message.answer("❌ Вы не можете удалить главного администратора!")
        return

    if admin_id not in ADMINS:
        await message.answer(f"❌ Пользователь с ID `{admin_id}` не является администратором.", parse_mode="Markdown")
        return

    ADMINS.remove(admin_id)
    if admin_id in ADMIN_NAMES:
        del ADMIN_NAMES[admin_id]

    await message.answer(
        f"✅ Администратор с ID `{admin_id}` успешно удален!",
        parse_mode="Markdown"
    )


@dp.message(Command("pause"))
async def pause_sales(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    global sales_paused
    sales_paused = True
    await message.answer("⏸ Продажи приостановлены!")


@dp.message(Command("resume"))
async def resume_sales(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    global sales_paused
    sales_paused = False
    await message.answer("▶️ Продажи возобновлены!")


@dp.message(Command("reset_daily"))
async def reset_daily_orders(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    global user_orders
    for user_id in user_orders:
        user_orders[user_id]["daily_orders"] = 0
        user_orders[user_id]["last_reset_day"] = datetime.now().day
    await message.answer("✅ Ежедневная статистика заказов сброшена!")


@dp.message(Command("reset_all"))
async def reset_all_orders(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    global user_orders, total_orders_all_time, product_stats, user_order_history
    user_orders = {}
    total_orders_all_time = 0
    product_stats = {}
    user_order_history = {}
    await message.answer("✅ **ВСЯ статистика заказов сброшена!**")


@dp.message(Command("aarssf"))
async def reset_orders(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    global user_orders
    user_orders = {}
    await message.answer("✅ Статистика заказов успешно сброшена!")


@dp.callback_query(lambda c: c.data == "catalog")
async def show_catalog(callback: types.CallbackQuery):
    add_user(callback.from_user.id)
    await callback.message.delete()
    status_text = "🔴 Продажи приостановлены" if sales_paused else "🟢 Продажи активны"
    await callback.message.answer(
        f"{status_text}\n\nВсе товары:",
        reply_markup=product_buttons()
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("product_"))
async def show_product(callback: types.CallbackQuery):
    add_user(callback.from_user.id)
    product_name = callback.data.replace("product_", "")
    if product_name not in PRODUCTS:
        await callback.message.answer("❌ Товар не найден.")
        await callback.answer()
        return

    data = PRODUCTS[product_name]

    keyboard = order_button(product_name) if not sales_paused else InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔴 Заказы временно недоступны", callback_data="no_order")]]
    )

    try:
        if data['photo'] and data['photo'] != "default.jpg":
            photo_path = data['photo']
            if os.path.exists(photo_path):
                await callback.message.answer_photo(
                    photo=types.FSInputFile(photo_path),
                    caption=f"📌 {product_name}\n💰 {data['price']}\n📝 {data['desc']}",
                    reply_markup=keyboard
                )
            else:
                await callback.message.answer(
                    f"📌 {product_name}\n💰 {data['price']}\n📝 {data['desc']}",
                    reply_markup=keyboard
                )
        else:
            await callback.message.answer(
                f"📌 {product_name}\n💰 {data['price']}\n📝 {data['desc']}",
                reply_markup=keyboard
            )
    except:
        await callback.message.answer(
            f"📌 {product_name}\n💰 {data['price']}\n📝 {data['desc']}",
            reply_markup=keyboard
        )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("order_"))
async def send_order(callback: types.CallbackQuery):
    global sales_paused

    add_user(callback.from_user.id)

    if sales_paused:
        await callback.message.answer(
            "🔴 Извините, продажи временно приостановлены.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="📦 Вернуться в каталог", callback_data="catalog")]]
            )
        )
        await callback.answer()
        return

    user_id = callback.from_user.id
    product_name = callback.data.replace("order_", "")

    can_order, error_message = check_order_limit(user_id)

    if not can_order:
        await callback.message.answer(
            f"{error_message}\n\nВы можете вернуться в каталог:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="📦 Вернуться в каталог", callback_data="catalog")]]
            )
        )
        await callback.answer()
        return

    username = callback.from_user.username or "нет username"

    order_text = (
        f"🛍 **Поступил новый заказ!**\n\n"
        f"📦 Товар: {product_name}\n"
        f"👤 Username: @{username}\n"
        f"🆔 ID: {user_id}"
    )

    for admin_id in ADMINS:
        try:
            await bot.send_message(chat_id=admin_id, text=order_text)
        except:
            pass

    update_user_order(user_id, product_name)

    await callback.message.answer(
        f"✅ Заказ создан! Мы свяжемся с вами в ближайшее время.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="📦 Вернуться в каталог", callback_data="catalog")]]
        )
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "no_order")
async def no_order_handler(callback: types.CallbackQuery):
    await callback.answer("Извините, заказы временно недоступны. Попробуйте позже.", show_alert=True)


async def main():
    if not os.path.exists("images"):
        os.makedirs("images")

    print("🤖 Бот готов для проверки...")
    print(f"\n👑 Главный администратор: {YOUR_TELEGRAM_ID}")
    print("\n📋 ДОСТУПНЫЕ КОМАНДЫ АДМИНА:")
    print("  /pause          - приостановить продажи")
    print("  /resume         - возобновить продажи")
    print("  /status         - полная статистика")
    print("  /reset_daily    - сбросить ежедневную статистику")
    print("  /reset_all      - сбросить ВСЮ статистику")
    print("  /add_admin ID   - добавить администратора")
    print("  /remove_admin ID - удалить администратора")
    print("  /admins         - список администраторов")
    print("  /setname Имя    - установить своё имя")
    print("  /add_product    - добавить новый товар")
    print("  /broadcast Текст - массовая рассылка")
    print("  /users_count    - количество пользователей")
    print("  /test Текст     - тестовая рассылка")
    print("  /aarssf         - сбросить данные пользователей")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())