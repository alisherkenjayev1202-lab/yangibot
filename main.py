from aiohttp import web
import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- 1. RENDER UCHUN VEB-SERVER (O'CHIB QOLMASLIGI UCHUN) ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render 10000-portni qidiradi
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()
    print("✅ Veb-server 10000-portda ishga tushdi")

# --- 2. SOZLAMALAR ---
API_TOKEN = '8770677204:AAFEcS1Iu5aseazXKVQwq9OYyn9RIJRUmGs'
ADMIN_ID = 7230209120

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class MovieAdd(StatesGroup):
    waiting_for_video = State()
    waiting_for_code = State()

# --- 3. BAZANI ISHGA TUSHIRISH ---
def init_db():
    conn = sqlite3.connect('kc_studio.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS movies 
                      (code TEXT PRIMARY KEY, file_id TEXT, title TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 4. PREMIUM TUGMALAR ---
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔍 Kino qidirish bo'yicha yordam", callback_data="help_search"))
    builder.row(
        types.InlineKeyboardButton(text="📱 Instagram", url="https://instagram.com/kenjayev_2330"),
        types.InlineKeyboardButton(text="📢 Telegram Kanal", url="https://t.me/+1Ge9CFu0Mwo2NjAy")
    )
    builder.row(types.InlineKeyboardButton(text="ℹ️ Biz haqimizda", callback_data="about"))
    return builder.as_markup()

# --- 5. BUYRUQLAR VA LOGIKA ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        f"🎬 **Kenjayev Cinema | KC Studio**\n\n"
        f"Assalomu alaykum, {message.from_user.first_name}!\n"
        "Botimizga xush kelibsiz. Kino ko'rish uchun uning **kodini** yozib yuboring.\n\n"
        "👇 Pastdagi menyudan foydalaning:"
    )
    if message.from_user.id == ADMIN_ID:
        welcome_text += "\n\n👨‍💻 **Admin:** Kino qo'shish uchun /add buyrug'ini bosing."
    await message.answer(welcome_text, reply_markup=get_main_menu(), parse_mode="Markdown")

@dp.callback_query(F.data == "help_search")
async def help_search(callback: types.CallbackQuery):
    await callback.message.answer("🔢 Kinoni qanday topish mumkin?\n\nJuda oson! Shunchaki kino kodini (masalan: 101) botga xabar qilib yuboring.")
    await callback.answer()

@dp.callback_query(F.data == "about")
async def about_kc(callback: types.CallbackQuery):
    await callback.message.answer("🎬 **KC Studio** — professional video va kino kontent platformasi.\nAsoschi: **Alisher Kenjayev**")
    await callback.answer()

@dp.message(Command("add"), F.from_user.id == ADMIN_ID)
async def start_add_movie(message: types.Message, state: FSMContext):
    await message.answer("📥 Menga kino **videosini** yuboring:")
    await state.set_state(MovieAdd.waiting_for_video)

@dp.message(MovieAdd.waiting_for_video, F.video)
async def save_video_id(message: types.Message, state: FSMContext):
    await state.update_data(v_id=message.video.file_id)
    await message.answer("✅ Video qabul qilindi. Endi bu kino uchun **maxsus kod** kiriting (masalan: 77):")
    await state.set_state(MovieAdd.waiting_for_code)

@dp.message(MovieAdd.waiting_for_code)
async def save_movie_to_db(message: types.Message, state: FSMContext):
    data = await state.get_data()
    m_code = message.text
    m_video = data['v_id']
    conn = sqlite3.connect('kc_studio.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO movies (code, file_id) VALUES (?, ?)", (m_code, m_video))
        conn.commit()
        await message.answer(f"🎉 **Muvaffaqiyatli!**\nKino bazaga qo'shildi. Kod: {m_code}", parse_mode="Markdown")
    except sqlite3.IntegrityError:
        await message.answer("⚠️ Bu kod bazada bor! Iltimos, boshqa kod kiriting.")
    finally:
        conn.close()
        await state.clear()

@dp.message()
async def search_movie(message: types.Message):
    query_code = message.text
    conn = sqlite3.connect('kc_studio.db')
    cursor = conn.cursor()
    cursor.execute("SELECT file_id FROM movies WHERE code=?", (query_code,))
    result = cursor.fetchone()
    conn.close()
    if result:
        await message.answer_video(
            video=result[0], 
            caption=f"🎬 **KC Studio taqdim etadi!**\n\n🔑 Kod: {query_code}\n🍿 Yoqimli hordiq tilaymiz!",
            parse_mode="Markdown"
        )
    else:
        if message.from_user.id != ADMIN_ID or not message.text.startswith('/'):
            await message.answer("😔 Kechirasiz, bu kod bilan kino topilmadi.\nIltimos, kodni to'g'ri yozganingizni tekshiring.")

# --- 6. ASOSIY ISHGA TUSHIRISH (BU YERGA QARA!) ---
async def main():
    # Render o'chib qolmasligi uchun serverni yoqish (MUHIM!)
    await start_server() 
    
    print("🚀 KC Studio boti ishga tushdi!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi!")