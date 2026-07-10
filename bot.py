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

ADMINS = {YOUR_TELEGRAM_ID}
ADMIN_NAMES = {}

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

user_orders = {}
sales_paused = False
total_orders_all_time = 0
product_stats = {}
user_order_history = {}
users_list = set()
TEMP_DATA = {}


def add_user(user_id: int):
    if user_id not in users_list:
        users_list.add(user_id)
        print(f"👤 Добавлен новый пользователь: {user_id}")


def is_admin(user_id: int) -> bool:
    return user_id in ADMINS


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
        inline_keyboard=[[InlineKeyboardButton(text="📦 Каталог", callback_data="catalog")]]
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
            [InlineKeyboardButton(text="✅ Оформить заказ", callback_data=f"order_{product_name}")]
        ]
    )


def admin_product_buttons():
    buttons = []
    for name in PRODUCTS.keys():
        buttons.append(InlineKeyboardButton(
            text=f"✏️ {name}",
            callback_data=f"edit_product_{name}"
        ))
    buttons.append(InlineKeyboardButton(
        text="➕ Добавить товар",
        callback_data="add_product_admin"
    ))
    keyboard = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def product_management_buttons(product_name):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать название", callback_data=f"edit_name_{product_name}")],
            [InlineKeyboardButton(text="💰 Редактировать цену", callback_data=f"edit_price_{product_name}")],
            [InlineKeyboardButton(text="📝 Редактировать описание", callback_data=f"edit_desc_{product_name}")],
            [InlineKeyboardButton(text="🖼 Редактировать фото", callback_data=f"edit_photo_{product_name}")],
            [InlineKeyboardButton(text="🗑 Удалить товар", callback_data=f"delete_product_{product_name}")],
            [InlineKeyboardButton(text="⬅️ Назад к управлению", callback_data="manage_products")]
        ]
    )


@dp.message(Command("start"))
async def start(message: types.Message):
    add_user(message.from_user.id)

    if is_admin(message.from_user.id):
        status_text = "🔴 Продажи приостановлены" if sales_paused else "🟢 Продажи активны"

        admin_name = ADMIN_NAMES.get(message.from_user.id)
        if not admin_name:
            try:
                user = await bot.get_chat(message.from_user.id)
                if user.username:
                    admin_name = f"@{user.username}"
                elif user.first_name:
                    admin_name = user.first_name
                else:
                    admin_name = str(message.from_user.id)
            except:
                admin_name = str(message.from_user.id)

        admins_list = []
        for admin_id in ADMINS:
            name = ADMIN_NAMES.get(admin_id)
            if not name:
                try:
                    user = await bot.get_chat(admin_id)
                    if user.username:
                        name = f"@{user.username}"
                    elif user.first_name:
                        name = user.first_name
                    else:
                        name = str(admin_id)
                except:
                    name = str(admin_id)
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
            f"📌 `/manage_products` - Управление товарами\n"
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
        name = ADMIN_NAMES.get(admin_id)
        if not name:
            try:
                user = await bot.get_chat(admin_id)
                if user.username:
                    name = f"@{user.username}"
                elif user.first_name:
                    name = user.first_name
                else:
                    name = str(admin_id)
            except:
                name = str(admin_id)

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
        new_name = ADMIN_NAMES.get(new_admin_id)
        if not new_name:
            try:
                user = await bot.get_chat(new_admin_id)
                if user.username:
                    new_name = f"@{user.username}"
                elif user.first_name:
                    new_name = user.first_name
                else:
                    new_name = str(new_admin_id)
            except:
                new_name = str(new_admin_id)

        await bot.send_message(
            chat_id=new_admin_id,
            text=f"🎉 **Поздравляю, {new_name}! Вы стали администратором бота!**\n\n"
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


@dp.message(Command("manage_products"))
async def manage_products(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    await message.answer(
        "🛍 **Управление товарами**\n\n"
        "Выберите товар для редактирования или удаления:\n"
        "Или нажмите 'Добавить товар' для создания нового.",
        reply_markup=admin_product_buttons()
    )


@dp.callback_query(lambda c: c.data == "manage_products")
async def manage_products_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    await callback.message.edit_text(
        "🛍 **Управление товарами**\n\n"
        "Выберите товар для редактирования или удаления:\n"
        "Или нажмите 'Добавить товар' для создания нового.",
        reply_markup=admin_product_buttons()
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "add_product_admin")
async def add_product_admin(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    TEMP_DATA[callback.from_user.id] = {}
    await callback.message.edit_text(
        "🛍 **Добавление нового товара**\n\n"
        "Введите название товара:\n"
        "(Отправьте 'отмена' чтобы отменить)"
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("edit_product_"))
async def edit_product_menu(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    product_name = callback.data.replace("edit_product_", "")
    if product_name not in PRODUCTS:
        await callback.answer("❌ Товар не найден.", show_alert=True)
        return

    data = PRODUCTS[product_name]
    await callback.message.edit_text(
        f"📌 **Редактирование товара:** {product_name}\n\n"
        f"💰 Цена: {data['price']}\n"
        f"📝 Описание: {data['desc']}\n"
        f"🖼 Фото: {'Есть' if data['photo'] and data['photo'] != 'default.jpg' else 'Нет'}\n\n"
        f"Выберите что хотите изменить:",
        reply_markup=product_management_buttons(product_name)
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("edit_name_"))
async def edit_product_name(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    product_name = callback.data.replace("edit_name_", "")
    TEMP_DATA[callback.from_user.id] = {"action": "edit_name", "product": product_name}
    await callback.message.edit_text(
        f"✏️ **Редактирование названия**\n\n"
        f"Текущее название: {product_name}\n\n"
        f"Введите новое название товара:\n"
        f"(Отправьте 'отмена' чтобы отменить)"
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("edit_price_"))
async def edit_product_price(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    product_name = callback.data.replace("edit_price_", "")
    TEMP_DATA[callback.from_user.id] = {"action": "edit_price", "product": product_name}
    await callback.message.edit_text(
        f"💰 **Редактирование цены**\n\n"
        f"Текущая цена: {PRODUCTS[product_name]['price']}\n\n"
        f"Введите новую цену товара:\n"
        f"(Отправьте 'отмена' чтобы отменить)"
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("edit_desc_"))
async def edit_product_desc(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    product_name = callback.data.replace("edit_desc_", "")
    TEMP_DATA[callback.from_user.id] = {"action": "edit_desc", "product": product_name}
    await callback.message.edit_text(
        f"📝 **Редактирование описания**\n\n"
        f"Текущее описание: {PRODUCTS[product_name]['desc']}\n\n"
        f"Введите новое описание товара:\n"
        f"(Отправьте 'отмена' чтобы отменить)"
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("edit_photo_"))
async def edit_product_photo(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    product_name = callback.data.replace("edit_photo_", "")
    TEMP_DATA[callback.from_user.id] = {"action": "edit_photo", "product": product_name}
    await callback.message.edit_text(
        f"🖼 **Редактирование фото**\n\n"
        f"Текущее фото: {'Есть' if PRODUCTS[product_name]['photo'] and PRODUCTS[product_name]['photo'] != 'default.jpg' else 'Нет'}\n\n"
        f"Отправьте новое фото товара:\n"
        f"(Отправьте 'пропустить' чтобы оставить текущее)"
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("delete_product_"))
async def delete_product(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    product_name = callback.data.replace("delete_product_", "")
    if product_name not in PRODUCTS:
        await callback.answer("❌ Товар не найден.", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{product_name}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="manage_products")]
        ]
    )

    await callback.message.edit_text(
        f"⚠️ **Подтверждение удаления**\n\n"
        f"Вы уверены, что хотите удалить товар:\n"
        f"📌 {product_name}\n\n"
        f"Это действие нельзя отменить!",
        reply_markup=keyboard
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("confirm_delete_"))
async def confirm_delete_product(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа.", show_alert=True)
        return

    product_name = callback.data.replace("confirm_delete_", "")
    if product_name not in PRODUCTS:
        await callback.answer("❌ Товар не найден.", show_alert=True)
        return

    del PRODUCTS[product_name]
    if product_name in product_stats:
        del product_stats[product_name]

    await callback.message.edit_text(
        f"✅ Товар **{product_name}** успешно удален!"
    )
    await callback.answer()


@dp.message()
async def handle_edit_product_steps(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    user_id = message.from_user.id
    if user_id not in TEMP_DATA:
        return

    data = TEMP_DATA[user_id]
    action = data.get("action")
    product_name = data.get("product")

    if message.text.lower() == "отмена":
        del TEMP_DATA[user_id]
        await message.answer("❌ Действие отменено.", reply_markup=admin_product_buttons())
        return

    if action == "edit_name":
        new_name = message.text.strip()
        if new_name in PRODUCTS and new_name != product_name:
            await message.answer("❌ Товар с таким названием уже существует!")
            return

        old_data = PRODUCTS[product_name]
        PRODUCTS[new_name] = old_data
        del PRODUCTS[product_name]

        if product_name in product_stats:
            product_stats[new_name] = product_stats[product_name]
            del product_stats[product_name]

        del TEMP_DATA[user_id]
        await message.answer(
            f"✅ Название товара успешно изменено!\n\n"
            f"Было: {product_name}\n"
            f"Стало: {new_name}",
            reply_markup=admin_product_buttons()
        )

    elif action == "edit_price":
        new_price = message.text.strip()
        PRODUCTS[product_name]["price"] = new_price
        del TEMP_DATA[user_id]
        await message.answer(
            f"✅ Цена товара **{product_name}** успешно обновлена!\n\n"
            f"Новая цена: {new_price}",
            reply_markup=admin_product_buttons()
        )

    elif action == "edit_desc":
        new_desc = message.text.strip()
        PRODUCTS[product_name]["desc"] = new_desc
        del TEMP_DATA[user_id]
        await message.answer(
            f"✅ Описание товара **{product_name}** успешно обновлено!",
            reply_markup=admin_product_buttons()
        )

    elif action == "edit_photo":
        if message.photo:
            old_photo = PRODUCTS[product_name].get("photo")
            if old_photo and old_photo != "default.jpg" and os.path.exists(old_photo):
                try:
                    os.remove(old_photo)
                except:
                    pass

            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)
            file_path = f"images/{product_name}_{int(time.time())}.jpg"
            await bot.download_file(file.file_path, file_path)
            PRODUCTS[product_name]["photo"] = file_path

            del TEMP_DATA[user_id]
            await message.answer(
                f"✅ Фото товара **{product_name}** успешно обновлено!",
                reply_markup=admin_product_buttons()
            )
        else:
            await message.answer("❌ Пожалуйста, отправьте фото.")


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


@dp.callback_query(lambda c: c.data.startswith("product_") and not c.data.startswith("product_management"))
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
    print("  /manage_products - управление товарами")
    print("  /broadcast Текст - массовая рассылка")
    print("  /users_count    - количество пользователей")
    print("  /test Текст     - тестовая рассылка")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())