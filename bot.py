import os
import io
import asyncio
import logging
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    BufferedInputFile
)

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

user_lang = {}

lang_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🇺🇿 O'zbekcha"), KeyboardButton(text="🇷🇺 Русский")],
        [KeyboardButton(text="🇬🇧 English")]
    ],
    resize_keyboard=True
)

async def search_archive_pdf(query: str, lang_code: str):
    lang_map = {"uz": "uzb", "ru": "rus", "en": "eng"}
    ia_lang = lang_map.get(lang_code, "eng")
    
    search_url = "https://archive.org"
    q_str = f'title:({query}) AND mediatype:(texts) AND language:({ia_lang})'
    params = {
        "q": q_str,
        "fl[]": ["identifier", "title", "creator"],
        "rows": 5,
        "output": "json"
    }
    
    results = []
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(search_url, params=params, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    docs = data.get("response", {}).get("docs", [])
                    for doc in docs:
                        ident = doc.get("identifier")
                        title = doc.get("title", query)
                        creator = doc.get("creator", "Noma'lum muallif")
                        if isinstance(creator, list):
                            creator = ", ".join(creator)
                        pdf_url = f"https://archive.org{ident}/{ident}.pdf"
                        results.append({
                            "title": title,
                            "author": creator,
                            "pdf_url": pdf_url,
                            "web_url": f"https://archive.org{ident}"
                        })
        except Exception as e:
            logging.error(f"Archive search error: {e}")
    return results

async def download_pdf_bytes(url: str):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=25) as resp:
                if resp.status == 200 and resp.content_length and resp.content_length < 45 * 1024 * 1024:
                    content_type = resp.headers.get("Content-Type", "")
                    if "pdf" in content_type or url.endswith(".pdf"):
                        return await resp.read()
        except Exception as e:
            logging.error(f"PDF download error: {e}")
    return None

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_lang[message.from_user.id] = "uz"
    await message.answer(
        "📚 Dunyo Kutubxonasi Botiga xush kelibsiz!\n\n"
        "Avval qaysi tilda kitob kerakligini tanlang, so'ngra kitob nomini yozing — men sizga PDF formatida topib beraman:",
        reply_markup=lang_keyboard,
        parse_mode="Markdown"
    )

@dp.message(F.text.in_(["🇺🇿 O'zbekcha", "🇷🇺 Русский", "🇬🇧 English"]))
async def set_language(message: types.Message):
    uid = message.from_user.id
    if "O'zbekcha" in message.text:
        user_lang[uid] = "uz"
        await message.answer("✅ O'zbek tili tanlandi. Endi kitob nomini yozing (masalan: *O'tkan kunlar*, *Alkimyogar*, *Python*):", parse_mode="Markdown")
    elif "Русский" in message.text:
        user_lang[uid] = "ru"
        await message.answer("✅ Выбран Русский язык. Напишите название книги (например: *Мастер и Маргарита*, *Преступление и наказание*):", parse_mode="Markdown")
    else:
        user_lang[uid] = "en"
        await message.answer("✅ English selected. Type the book name (e.g., *Atomic Habits*, *Sherlock Holmes*, *Python*):", parse_mode="Markdown")
[20/11/2026 12:59] Shaxnoza Amirqulova: @dp.message(F.text)
async def handle_book_query(message: types.Message):
    uid = message.from_user.id
    lang = user_lang.get(uid, "uz")
    query = message.text.strip()
    
    wait_msg = await message.answer("🔍 Dunyo kutubxonasidan PDF qidirilmoqda, biroz kuting...")
    books = await search_archive_pdf(query, lang)
    
    if not books:
        await wait_msg.edit_text("😔 Afsuski, bu tilda ushbu kitobning ochiq PDF varianti topilmadi. Kitob nomini to'liqroq yoki muallifi bilan yozib ko'ring.")
        return

    await wait_msg.edit_text(f"📚 {len(books)} ta natija topildi, PDF tayyorlanmoqda...")

    for book in books[:3]:
        title = str(book["title"])[:60]
        author = str(book["author"])[:50]
        pdf_bytes = await download_pdf_bytes(book["pdf_url"])
        
        if pdf_bytes:
            file_name = f"{title}.pdf".replace("/", "_")
            doc_file = BufferedInputFile(pdf_bytes, filename=file_name)
            await message.answer_document(
                document=doc_file,
                caption=f"📖 {title}\n✍️ Muallif: {author}\n🌐 Til: {lang.upper()}",
                parse_mode="Markdown"
            )
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📥 PDF yuklab olish / O'qish", url=book["web_url"])]
            ])
            await message.answer(
                f"📖 {title}\n✍️ Muallif: {author}\n🌐 Til: {lang.upper()}",
                reply_markup=kb,
                parse_mode="Markdown"
            )
    await wait_msg.delete()

async def handle_ping(request):
    return web.Response(text="Bot ishlayapti!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    logging.basicConfig(level=logging.INFO)
    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

asyncio.run(main())
