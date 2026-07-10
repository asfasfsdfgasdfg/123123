import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.client.session.aiohttp import AiohttpSession


session = AiohttpSession(timeout=300)


TOKEN = "8953142991:AAEH2bhrfROc8358a0dseSh5Hb04gPS0Xf4"
YOUR_TELEGRAM_ID = 1795960713  # Ваш ID


PRODUCTS = {
    "Товар 1": {"price": "n руб.", "desc": "abc", "photo": "421.png"},
    "Товар 2": {"price": "n руб.", "desc": "abc", "photo": "321.png"},
    "Товар 3": {"price": "n руб.", "desc": "abc", "photo": "123.jpg"},
}

bot = Bot(token=TOKEN, session=session)
dp = Dispatcher()

# ===== КЛАВИАТУРЫ =====
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
    await message.answer(
        " \nНажмите кнопку ниже чтобы посмотреть каталог:",
        reply_markup=catalog_button()
    )

@dp.callback_query(lambda c: c.data == "catalog")
async def show_catalog(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "Все товары:\n:",
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
        f" **Поступил новый заказ, инфа ниже!**\n\n"
        f" Товар: {product_name}\n"
        f" Username: @{username}\n"
        f" ID: {user_id}"
    )

    await bot.send_message(chat_id=YOUR_TELEGRAM_ID, text=order_text)

    await callback.message.answer(
        "✅ Заказ создан! Мы свяжемся с вами в ближайшее время.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="📦Вернуться в каталог", callback_data="catalog")]]
        )
    )
    await callback.answer()

# ===== ЗАПУСК =====
async def main():
    print("Бот готов для проверки...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())