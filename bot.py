
import os
import asyncio
import logging
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def search_books(query: str):
    base = "https://gutendex.com"
    params = {"search": query}
    async with aiohttp.ClientSession() as session:
        async with session.get(base, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("results", [])[:5]
    return []

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "📚 Dunyo Kutubxonasi Botiga xush kelibsiz!\n\n"
        "Istalgan kitob yoki muallif nomini yozing (masalan: Harry Potter, Sherlock Holmes, Dostoevsky).\n"
        "Men sizga dunyo bazasidan topib, yuklab olish havolasini beraman!"
    )

@dp.message(F.text)
async def handle_search(message: types.Message):
    query = message.text.strip()
    wait_msg = await message.answer("🔍 Dunyo kutubxonasidan qidirilmoqda...")
    
    books = await search_books(query)
    await wait_msg.delete()

    if not books:
        await message.answer("😔 Afsuski, bu nom bilan kitob topilmadi. Kitobning asl yoki inglizcha nomini yozib ko'ring.")
        return

    for book in books:
        title = book.get("title", "Noma'lum kitob")
        authors = ", ".join([a["name"] for a in book.get("authors", [])]) or "Noma'lum muallif"
        formats = book.get("formats", {})
        
        download_url = (
            formats.get("application/epub+zip") or 
            formats.get("text/plain; charset=utf-8") or 
            formats.get("text/html")
        )

        if download_url:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📥 Kitobni yuklab olish / O'qish", url=download_url)]
            ])
            await message.answer(
                f"📖 Kitob: {title}\n"
                f"✍️ Muallif: {authors}",
                reply_markup=keyboard
            )

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
