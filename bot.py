import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.client.session.aiohttp import AiohttpSession

# ===== НАСТРОЙКИ ПОДКЛЮЧЕНИЯ (С УВЕЛИЧЕННЫМ ТАЙМАУТОМ) =====
# Увеличиваем таймаут до 5 минут (300 секунд)
session = AiohttpSession(timeout=300)

# ===== НАСТРОЙКИ =====
TOKEN = "8840106422:AAGpM6GLcfZlvfUW8aJPCUtLcSGSbF03434"  # Вставьте новый токен от @BotFather
YOUR_TELEGRAM_ID = 1795960713  # Ваш ID

# ===== ТОВАРЫ =====
PRODUCTS = {
    "Говно с маслом": {"price": "5000 руб.", "desc": "вкусно и недорого", "photo": "421.png"},
    "Пенис мытый": {"price": "1200 руб.", "desc": "нормалдаке", "photo": "321.png"},
    "Пенис немытый": {"price": "8000 руб.", "desc": "так себе", "photo": "123.jpg"},
}

# ===== ИНИЦИАЛИЗАЦИЯ (С УВЕЛИЧЕННЫМ ТАЙМАУТОМ) =====
bot = Bot(token=TOKEN, session=session)
dp = Dispatcher()

# ===== КЛАВИАТУРЫ =====
def catalog_button():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=" Каталог", callback_data="catalog")]]
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
            [InlineKeyboardButton(text=" Накакать чуть чуть", callback_data=f"order_{product_name}")]
        ]
    )

# ===== ОБРАБОТЧИКИ КОМАНД =====
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Хай гитлер! \nнасри ниже чтобы почекать че продаю:",
        reply_markup=catalog_button()
    )

@dp.callback_query(lambda c: c.data == "catalog")
async def show_catalog(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        " вот всякое говно:\nвыбери че хочш:",
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
    product_name = callback.data.replace("order_", "")
    username = callback.from_user.username or "нет username"
    user_id = callback.from_user.id

    order_text = (
        f"🔔 **НОВЫЙ ЗАКАЗ!**\n\n"
        f"🛒 Товар: {product_name}\n"
        f"👤 Username: @{username}\n"
        f"🆔 ID: {user_id}"
    )

    await bot.send_message(chat_id=YOUR_TELEGRAM_ID, text=order_text)

    await callback.message.answer(
        "✅ Все иди нахуй! Пока.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="📦 Пук пук пук", callback_data="catalog")]]
        )
    )
    await callback.answer()

# ===== ЗАПУСК =====
async def main():
    print("✅ Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())