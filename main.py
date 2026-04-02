import os
import asyncio
import logging
import ssl
import certifi
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from pymongo import MongoClient

# --- 1. RENDER UCHUN VEB-SERVER ---
async def handle(request):
    return web.Response(text="KC Studio Bot is Online 24/7!")

async def start_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10001))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"✅ Veb-server {port}-portda ishga tushdi")

# --- 2. SOZLAMALAR ---
API_TOKEN = '8770677204:AAFEcS1Iu5aseazXKVQwq9OYyn9RIJRUmGs'
ADMIN_ID = 7230209120
MONGO_URL = "mongodb+srv://alisherkenjayev1202_db_user:Y1SSUvfYGkjQsoQw@cluster0.rcko5fk.mongodb.net/kc_studio_db?retryWrites=true&w=majority&appName=Cluster0"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- SSL VA MONGODB ULANISHI ---
try:
    ca = certifi.where()
    client = MongoClient(MONGO_URL, tlsCAFile=ca, serverSelectionTimeoutMS=5000)
    db = client['kc_studio_db']
    movies_col = db['movies']
    users_col = db['users']  # YANGI: Foydalanuvchilar bazasi
    client.admin.command('ping')
    print("✅ MongoDB-ga muvaffaqiyatli ulandi!")
except Exception as e:
    print(f"❌ MongoDB-ga ulanishda xato: {e}")

class MovieAdd(StatesGroup):
    waiting_for_video = State()
    waiting_for_code = State()

# --- 3. PREMIUM TUGMALAR ---
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔍 Kino qidirish bo'yicha yordam", callback_data="help_search"))
    builder.row(
        types.InlineKeyboardButton(text="📱 Instagram", url="https://instagram.com/kenjayev_2330"),
        types.InlineKeyboardButton(text="📢 Telegram Kanal", url="https://t.me/+1Ge9CFu0Mwo2NjAy")
    )
    builder.row(types.InlineKeyboardButton(text="ℹ️ Biz haqimizda", callback_data="about"))
    return builder.as_markup()

# --- 4. BUYRUQLAR VA LOGIKA ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # --- STATISTIKA UCHUN FOYDALANUVCHINI RO'YXATGA OLISH ---
    user_id = message.from_user.id
    if not users_col.find_one({"user_id": user_id}):
        users_col.insert_one({"user_id": user_id})
    
    welcome_text = (
        f"🎬 **Kenjayev Cinema | KC Studio**\n\n"
        f"Assalomu alaykum, {message.from_user.first_name}!\n"
        "Botimizga xush kelibsiz. Kino ko'rish uchun uning **kodini** yozib yuboring."
    )
    
    if message.from_user.id == ADMIN_ID:
        welcome_text += "\n\n👨‍💻 **Admin paneli:**\n/add - Kino qo'shish\n/stat - Foydalanuvchilar soni"
        
    await message.answer(welcome_text, reply_markup=get_main_menu(), parse_mode="Markdown")

# --- YANGI: ADMIN UCHUN STATISTIKA BUYRUG'I ---
@dp.message(Command("stat"), F.from_user.id == ADMIN_ID)
async def cmd_stat(message: types.Message):
    count = users_col.count_documents({})
    await message.answer(f"📊 **Bot statistikasi**\n\nFoydalanuvchilar soni: **{count}** ta", parse_mode="Markdown")

@dp.callback_query(F.data == "help_search")
async def help_search(callback: types.CallbackQuery):
    await callback.message.answer("🔢 Kinoni qanday topish mumkin?\n\nJuda oson! Shunchaki kino kodini (masalan: 101) botga yozib yuboring.")
    await callback.answer()

@dp.callback_query(F.data == "about")
async def about_kc(callback: types.CallbackQuery):
    await callback.message.answer("🎬 **KC Studio** — professional kino kontent platformasi.\nAsoschi: **Alisher Kenjayev**")
    await callback.answer()

# --- ADMIN: KINO QO'SHISH ---
@dp.message(Command("add"), F.from_user.id == ADMIN_ID)
async def start_add_movie(message: types.Message, state: FSMContext):
    await message.answer("📥 Menga kino **videosini** yuboring:")
    await state.set_state(MovieAdd.waiting_for_video)

@dp.message(MovieAdd.waiting_for_video, F.video)
async def save_video_id(message: types.Message, state: FSMContext):
    await state.update_data(v_id=message.video.file_id)
    await message.answer("✅ Video qabul qilindi. Endi kino uchun **kod** kiriting:")
    await state.set_state(MovieAdd.waiting_for_code)

@dp.message(MovieAdd.waiting_for_code)
async def save_movie_to_db(message: types.Message, state: FSMContext):
    data = await state.get_data()
    m_code = message.text
    try:
        if movies_col.find_one({"code": m_code}):
            await message.answer("⚠️ Bu kod bazada bor! Boshqa kod kiriting.")
        else:
            movies_col.insert_one({"code": m_code, "file_id": data['v_id']})
            await message.answer(f"🎉 **Muvaffaqiyatli!**\nKino bazaga qo'shildi. Kod: {m_code}", parse_mode="Markdown")
            await state.clear()
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")

# --- FOYDALANUVCHI: KINO QIDIRISH ---
@dp.message()
async def search_movie(message: types.Message):
    if message.text and not message.text.startswith('/'):
        try:
            res = movies_col.find_one({"code": message.text})
            if res:
                await message.answer_video(
                    video=res['file_id'], 
                    caption=f"🎬 **KC Studio taqdim etadi!**\n\n🔑 Kod: {message.text}\n🍿 Yoqimli hordiq!",
                    parse_mode="Markdown"
                )
            else:
                await message.answer("😔 Bu kod bilan kino topilmadi.")
        except Exception as e:
            logging.error(f"Qidiruv xatosi: {e}")
            await message.answer("⚠️ Baza bilan ulanishda muammo bo'ldi.")

# --- 5. ASOSIY ISHGA TUSHIRISH ---
async def main():
    await start_server() 
    print("🚀 KC Studio boti ishga tushdi!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try: 
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi!")