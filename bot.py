"""
Manhwa Tarjimon Bot
--------------------
Foydalanuvchi Telegramga manhwa varog'i (rasm) yuboradi — RASM SIFATIDA HAM,
FAYL (DOCUMENT) SIFATIDA HAM qabul qilinadi.
Bot rasmdagi inglizcha matnni o'zbek tiliga tarjima qilib, FAYL sifatida
(sifat yo'qotilmasdan) qaytaradi.

BOT_TOKEN Railway'da "Variables" bo'limida o'rnatiladi (kodga yozilmaydi).
"""

import io
import logging
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import easyocr
from deep_translator import GoogleTranslator
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = (os.environ.get("BOT_TOKEN") or "").strip()

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN topilmadi! Railway 'Variables' bo'limida BOT_TOKEN "
        "nomli o'zgaruvchi yaratilganiga va qiymati to'g'ri kiritilganiga ishonch hosil qiling."
    )

logger.info(f"Token yuklandi, uzunligi: {len(BOT_TOKEN)} belgi")

reader = easyocr.Reader(["en"], gpu=False)


def translate_text(text: str) -> str:
    try:
        return GoogleTranslator(source="en", target="uz").translate(text)
    except Exception as e:
        logger.warning(f"Tarjima xatosi: {e}")
        return text


def process_image(image: Image.Image) -> Image.Image:
    img_np = np.array(image.convert("RGB"))
    results = reader.readtext(img_np)

    draw_img = image.convert("RGB").copy()
    draw = ImageDraw.Draw(draw_img)

    for bbox, text, confidence in results:
        if not text.strip() or confidence < 0.3:
            continue

        translated = translate_text(text)

        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)

        draw.rectangle([x0, y0, x1, y1], fill="white")

        box_height = max(int(y1 - y0), 10)
        font_size = max(int(box_height * 0.8), 10)
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

        draw.text((x0, y0), translated, fill="black", font=font)

    return draw_img


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Assalomu alaykum! Menga manhwa varog'ining rasmini yuboring "
        "(fayl yoki rasm sifatida), men uni o'zbekchaga tarjima qilib beraman 📖"
    )


async def _process_and_reply(update: Update, image: Image.Image):
    await update.message.reply_text("Rasm qabul qilindi, ishlanyapti... ⏳")

    try:
        result_image = process_image(image)
    except Exception as e:
        logger.exception("Rasmni qayta ishlashda xato")
        await update.message.reply_text(f"Xatolik yuz berdi: {e}")
        return

    output = io.BytesIO()
    result_image.save(output, format="PNG")
    output.seek(0)

    # Fayl sifatida yuboramiz - sifat yo'qolmasligi uchun
    await update.message.reply_document(
        document=InputFile(output, filename="tarjima.png"),
        caption="Tayyor ✅",
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    image = Image.open(io.BytesIO(bytes(photo_bytes)))
    await _process_and_reply(update, image)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.mime_type or not doc.mime_type.startswith("image/"):
        await update.message.reply_text(
            "Bu fayl rasm emas ko'rinadi. Iltimos, rasm faylini yuboring."
        )
        return

    doc_file = await doc.get_file()
    doc_bytes = await doc_file.download_as_bytearray()
    image = Image.open(io.BytesIO(bytes(doc_bytes)))
    await _process_and_reply(update, image)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Menga manhwa varog'ining rasmini yuboring (fayl yoki rasm sifatida), "
        "men uni o'zbekchaga tarjima qilib beraman 📖"
    )


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.COMMAND, handle_start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
