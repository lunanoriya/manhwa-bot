"""
Manhwa Tarjimon Bot
--------------------
Foydalanuvchi Telegramga manhwa varog'i (rasm) yuboradi.
Bot:
 1) Rasmdagi inglizcha matnni OCR bilan topadi (matn + koordinatalari)
 2) Har bir matn bo'lagini o'zbek tiliga tarjima qiladi
 3) Eski matnni oq to'rtburchak bilan yopadi va o'rniga tarjimani yozadi
 4) Tayyor rasmni foydalanuvchiga qaytaradi

O'RNATISH (terminalda, bir marta):
    pip install python-telegram-bot easyocr deep-translator pillow numpy

ISHGA TUSHIRISH:
    1) Pastda BOT_TOKEN o'rniga BotFather bergan tokenni yozing
    2) python bot.py

BotFather'dan token olish:
    Telegramda @BotFather ga yozing -> /newbot -> nomini bering -> u sizga token beradi
"""

import io
import logging
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import easyocr
from deep_translator import GoogleTranslator
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# OCR reader'ni bir marta yuklaymiz (inglizcha matn uchun)
reader = easyocr.Reader(["en"])


def translate_text(text: str) -> str:
    """Inglizcha matnni o'zbek tiliga tarjima qiladi."""
    try:
        return GoogleTranslator(source="en", target="uz").translate(text)
    except Exception as e:
        logger.warning(f"Tarjima xatosi: {e}")
        return text


def process_image(image: Image.Image) -> Image.Image:
    """Rasmdagi inglizcha matnni topib, o'zbekcha tarjima bilan almashtiradi."""
    img_np = np.array(image.convert("RGB"))
    results = reader.readtext(img_np)  # [(bbox, text, confidence), ...]

    draw_img = image.convert("RGB").copy()
    draw = ImageDraw.Draw(draw_img)

    for bbox, text, confidence in results:
        if not text.strip() or confidence < 0.3:
            continue

        translated = translate_text(text)

        # bbox — 4 ta burchak koordinatasi: [top-left, top-right, bottom-right, bottom-left]
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)

        # Eski matnni oq to'rtburchak bilan yopish
        draw.rectangle([x0, y0, x1, y1], fill="white")

        # Matn balandligiga qarab shrift o'lchamini hisoblash
        box_height = max(int(y1 - y0), 10)
        font_size = max(int(box_height * 0.8), 10)
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

        draw.text((x0, y0), translated, fill="black", font=font)

    return draw_img


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Rasm qabul qilindi, ishlanyapti... ⏳")

    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    image = Image.open(io.BytesIO(bytes(photo_bytes)))

    try:
        result_image = process_image(image)
    except Exception as e:
        logger.exception("Rasmni qayta ishlashda xato")
        await update.message.reply_text(f"Xatolik yuz berdi: {e}")
        return

    output = io.BytesIO()
    output.name = "tarjima.png"
    result_image.save(output, format="PNG")
    output.seek(0)

    await update.message.reply_photo(photo=output, caption="Tayyor ✅")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Menga manhwa varog'ining rasmini yuboring, men uni o'zbekchaga tarjima qilib beraman 📖"
    )


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
