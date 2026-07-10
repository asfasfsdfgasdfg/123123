import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.client.session.aiohttp import AiohttpSession
from datetime import datetime
import time

session = AiohttpSession(timeout=300)

TOKEN = "8953142991:AAEH2bhrfROc8358a0dseSh5Hb04gPS0Xf4"
YOUR_TELEGRAM_ID = 1795960713  # Ваш ID


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


user_orders = {}  # {user_id: {"last_order_time": timestamp, "daily_orders": count, "last_reset_day": day_number}}


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

    data = get_user_order_data(user_id)
    data["last_order_time"] = time.time()
    data["daily_orders"] += 1



def catalog_button():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💼 Каталог", callback_data="catalog")]]
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
    await message.answer(
        "Нажмите кнопку ниже чтобы посмотреть каталог:",
        reply_markup=catalog_button()
    )



@dp.message(Command("aarssf"))
async def reset_orders(message: types.Message):


    if message.from_user.id != YOUR_TELEGRAM_ID:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    
    global user_orders
    user_orders = {}

    await message.answer(
        "✅ Статистика заказов успешно сброшена!\n\n"
        f"Все пользователи могут снова делать заказы.\n"
        f"Количество пользователей в кэше: 0"
    )


@dp.callback_query(lambda c: c.data == "catalog")
async def show_catalog(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "Все товары:",
        reply_markup=product_buttons()
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("product_"))
async def show_product(callback: types.CallbackQuery):
    product_name = callback.data.replace("product_", "")
    data = PRODUCTS[product_name]
    photo_path = f"images/{data['photo']}"

    await callback.message.answer_photo(
        photo=types.FSInputFile(photo_path),
        caption=f"📌 {product_name}\n💰 {data['price']}\n📝 {data['desc']}",
        reply_markup=order_button(product_name)
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("order_"))
async def send_order(callback: types.CallbackQuery):
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



async def main():
    print("Бот готов для проверки...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())