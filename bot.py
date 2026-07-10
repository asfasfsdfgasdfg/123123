import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.client.session.aiohttp import AiohttpSession
from datetime import datetime
import time

session = AiohttpSession(timeout=300)

TOKEN = "8953142991:AAEH2bhrfROc8358a0dseSh5Hb04gPS0Xf4"
YOUR_TELEGRAM_ID = 1795960713

# ===== СПИСОК АДМИНИСТРАТОРОВ =====
ADMINS = {YOUR_TELEGRAM_ID}  # Множество ID администраторов
ADMIN_NAMES = {}  # {user_id: "имя"} - для хранения пользовательских имен администраторов

ANTISPAM_SETTINGS = {
    "min_time_between_orders": 30,
    "max_orders_per_day": 5,
}

PRODUCTS = {
    "Товар 1": {"price": "n руб.", "desc": "abc", "photo": "421.png"},
    "Товар 2": {"price": "n руб.", "desc": "abc", "photo": "321.png"},
    "Товар 3": {"price": "n руб.", "desc": "abc", "photo": "123.jpg"},
}

bot = Bot(token=TOKEN, session=session)
dp = Dispatcher()

user_orders = {}
sales_paused = False
total_orders_all_time = 0


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


def update_user_order(user_id: int):
    global total_orders_all_time
    data = get_user_order_data(user_id)
    data["last_order_time"] = time.time()
    data["daily_orders"] += 1
    total_orders_all_time += 1


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


@dp.message(Command("start"))
async def start(message: types.Message):
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
            f"👥 Пользователей: {len(user_orders)}\n\n"
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
            "Например: `/setname Алексей`\n\n"
            "Имя будет отображаться в приветствии и списке администраторов."
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
        f"Всего: {len(ADMINS)} администраторов\n\n"
        f"⭐ - Главный администратор (не может быть удален)",
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
            "Используйте: `/add_admin 123456789`\n"
            "Где 123456789 - это ID пользователя Telegram."
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
        f"✅ Администратор с ID `{new_admin_id}` успешно добавлен!\n\n"
        f"Теперь этот пользователь имеет доступ ко всем админ-командам.",
        parse_mode="Markdown"
    )

    try:
        
        new_admin_name = get_admin_name(new_admin_id)
        await bot.send_message(
            chat_id=new_admin_id,
            text=f"🎉 **Поздравляю, {new_admin_name}! Вы стали администратором бота!**\n\n"
                 f"Теперь вам доступны все команды управления:\n"
                 f"• `/pause` - приостановить продажи\n"
                 f"• `/resume` - возобновить продажи\n"
                 f"• `/status` - статистика\n"
                 f"• `/reset_daily` - сброс ежедневной статистики\n"
                 f"• `/reset_all` - полный сброс\n"
                 f"• `/add_admin` - добавить администратора\n"
                 f"• `/remove_admin` - удалить администратора\n"
                 f"• `/setname` - установить своё имя\n\n"
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
            "Используйте: `/remove_admin 123456789`\n"
            "Где 123456789 - это ID пользователя Telegram."
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
        f"✅ Администратор с ID `{admin_id}` успешно удален!\n\n"
        f"Этот пользователь больше не имеет доступа к админ-командам.",
        parse_mode="Markdown"
    )


@dp.message(Command("pause"))
async def pause_sales(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    global sales_paused
    sales_paused = True
    await message.answer(
        "⏸ Продажи приостановлены!\n\n"
        "Пользователи смогут просматривать каталог, но не смогут оформлять заказы.\n"
        "Для возобновления используйте /resume"
    )


@dp.message(Command("resume"))
async def resume_sales(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    global sales_paused
    sales_paused = False
    await message.answer(
        "▶️ Продажи возобновлены!\n\n"
        "Пользователи снова могут оформлять заказы."
    )


@dp.message(Command("status"))
async def sales_status(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    status = "🔴 ПРИОСТАНОВЛЕНЫ" if sales_paused else "🟢 АКТИВНЫ"
    users_count = len(user_orders)
    daily_orders = sum(data["daily_orders"] for data in user_orders.values())
    await message.answer(
        f"📊 **СТАТИСТИКА ПРОДАЖ:**\n\n"
        f"📌 Статус: {status}\n"
        f"👥 Пользователей в кэше: {users_count}\n"
        f"📦 Заказов сегодня: {daily_orders}\n"
        f"🏆 Заказов за все время: {total_orders_all_time}"
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
    await message.answer(
        "✅ Ежедневная статистика заказов сброшена!\n\n"
        f"Все пользователи могут снова делать заказы.\n"
        f"Всего за все время: {total_orders_all_time} заказов"
    )


@dp.message(Command("reset_all"))
async def reset_all_orders(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    global user_orders, total_orders_all_time
    user_orders = {}
    total_orders_all_time = 0
    await message.answer(
        "✅ **ВСЯ статистика заказов сброшена!**\n\n"
        "Сброшено:\n"
        "• Ежедневная статистика\n"
        "• Статистика за все время\n"
        "• Данные всех пользователей\n\n"
        "Все пользователи могут снова делать заказы."
    )


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
    await callback.message.delete()
    status_text = "🔴 Продажи приостановлены" if sales_paused else "🟢 Продажи активны"
    await callback.message.answer(
        f"{status_text}\n\nВсе товары:",
        reply_markup=product_buttons()
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("product_"))
async def show_product(callback: types.CallbackQuery):
    product_name = callback.data.replace("product_", "")
    data = PRODUCTS[product_name]
    photo_path = f"images/{data['photo']}"

    keyboard = order_button(product_name) if not sales_paused else InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔴 Заказы временно недоступны", callback_data="no_order")]]
    )

    await callback.message.answer_photo(
        photo=types.FSInputFile(photo_path),
        caption=f"📌 {product_name}\n💰 {data['price']}\n📝 {data['desc']}",
        reply_markup=keyboard
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("order_"))
async def send_order(callback: types.CallbackQuery):
    global sales_paused

    if sales_paused:
        await callback.message.answer(
            "🔴 Извините, продажи временно приостановлены.\n\n"
            "Пожалуйста, попробуйте позже.",
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
        f"🛍 **Поступил новый заказ, инфа ниже!**\n\n"
        f"📦 Товар: {product_name}\n"
        f"👤 Username: @{username}\n"
        f"🆔 ID: {user_id}"
    )

    await bot.send_message(chat_id=YOUR_TELEGRAM_ID, text=order_text)
    update_user_order(user_id)

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
    print("Бот готов для проверки...")
    print(f"\n👑 Главный администратор: {YOUR_TELEGRAM_ID}")
    print("\n📋 ДОСТУПНЫЕ КОМАНДЫ АДМИНА:")
    print("  /pause          - приостановить продажи")
    print("  /resume         - возобновить продажи")
    print("  /status         - статус продаж и статистика")
    print("  /reset_daily    - сбросить ежедневную статистику")
    print("  /reset_all      - сбросить ВСЮ статистику")
    print("  /add_admin ID   - добавить администратора")
    print("  /remove_admin ID - удалить администратора")
    print("  /admins         - список администраторов")
    print("  /setname Имя    - установить своё имя")
    print("  /aarssf         - сбросить данные пользователей")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())