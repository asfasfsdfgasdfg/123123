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
    # Проверяем, админ ли это
    if message.from_user.id == YOUR_TELEGRAM_ID:
        # Панель администратора
        status_text = "🔴 Продажи приостановлены" if sales_paused else "🟢 Продажи активны"
        await message.answer(
            f"👋 **Приветствую!**\n\n"
            f"📊 Текущий статус: {status_text}\n"
            f"📦 Всего заказов: {total_orders_all_time}\n"
            f"👥 Пользователей: {len(user_orders)}\n\n"
            f"🔧 **Доступные команды:**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 `/pause` - Приостановить продажи\n"
            f"📌 `/resume` - Возобновить продажи\n"
            f"📌 `/status` - Полная статистика\n"
            f"📌 `/reset_daily` - Сброс ежедневной статистики\n"
            f"📌 `/reset_all` - Полный сброс ВСЕЙ статистики\n"
            f"📌 `/aarssf` - Сброс данных пользователей\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Для просмотра каталога нажмите кнопку ниже:",
            reply_markup=catalog_button()
        )
    else:
        # Обычный пользователь
        status_text = "🔴 Продажи приостановлены" if sales_paused else "🟢 Продажи активны"
        await message.answer(
            f"{status_text}\n\nНажмите кнопку ниже чтобы посмотреть каталог:",
            reply_markup=catalog_button()
        )


@dp.message(Command("pause"))
async def pause_sales(message: types.Message):
    global sales_paused
    if message.from_user.id != YOUR_TELEGRAM_ID:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    sales_paused = True
    await message.answer(
        "⏸ Продажи приостановлены!\n\n"
        "Пользователи смогут просматривать каталог, но не смогут оформлять заказы.\n"
        "Для возобновления используйте /resume"
    )


@dp.message(Command("resume"))
async def resume_sales(message: types.Message):
    global sales_paused
    if message.from_user.id != YOUR_TELEGRAM_ID:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    sales_paused = False
    await message.answer(
        "▶️ Продажи возобновлены!\n\n"
        "Пользователи снова могут оформлять заказы."
    )


@dp.message(Command("status"))
async def sales_status(message: types.Message):
    if message.from_user.id != YOUR_TELEGRAM_ID:
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
        f"🏆 Заказов за все время: {total_orders_all_time}\n"
        f"⏱ Время: {datetime.now().strftime('%H:%M:%S')}"
    )


@dp.message(Command("reset_daily"))
async def reset_daily_orders(message: types.Message):
    if message.from_user.id != YOUR_TELEGRAM_ID:
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
    if message.from_user.id != YOUR_TELEGRAM_ID:
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
    if message.from_user.id != YOUR_TELEGRAM_ID:
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
    print("\n📋 ДОСТУПНЫЕ КОМАНДЫ АДМИНА:")
    print("  /pause      - приостановить продажи")
    print("  /resume     - возобновить продажи")
    print("  /status     - статус продаж и статистика")
    print("  /reset_daily - сбросить ежедневную статистику")
    print("  /reset_all  - сбросить ВСЮ статистику")
    print("  /aarssf     - сбросить данные пользователей")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())