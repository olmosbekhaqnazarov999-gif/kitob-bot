@dp.message(F.text)
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
