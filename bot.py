"""
Manhwa Tarjimon Bot (yengil versiya)
--------------------------------------
Og'ir mahalliy OCR (easyocr) o'rniga bulutli OCR.space xizmatidan
foydalanadi - bu Railway'ning bepul serverida xotira yetishmasligi
muammosini bartaraf etadi.
Kerakli muhit o'zgaruvchilari (Railway "Variables" bo'limida):
  BOT_TOKEN   - Telegram bot tokeni
  OCR_API_KEY - OCR.space bepul API kaliti (https://ocr.space/ocrapi dan olinadi)
                Agar kiritilmasa, sinov (juda cheklangan) kalit ishlatiladi.
"""
import io
import logging
import os
import requests
from PIL import Image, ImageDraw, ImageFont
from deep_translator import GoogleTranslator
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
BOT_TOKEN = (os.environ.get("BOT_TOKEN") or "").strip()
OCR_API_KEY = (os.environ.get("OCR_API_KEY") or "helloworld").strip()
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN topilmadi! Railway 'Variables' bo'limida BOT_TOKEN "
        "nomli o'zgaruvchi yaratilganiga va qiymati to'g'ri kiritilganiga ishonch hosil qiling."
    )
logger.info(f"Token yuklandi, uzunligi: {len(BOT_TOKEN)} belgi")
def translate_text(text: str) -> str:
    try:
        return GoogleTranslator(source="en", target="uz").translate(text)
    except Exception as e:
        logger.warning(f"Tarjima xatosi: {e}")
        return text
def ocr_space_extract(image_bytes: bytes):
    """OCR.space API orqali matn va koordinatalarni olamiz."""
    response = requests.post(
        "https://api.ocr.space/parse/image",
        files={"file": ("image.png", image_bytes)},
        data={
            "apikey": OCR_API_KEY,
            "language": "eng",
            "isOverlayRequired": True,
            "OCREngine": 2,
        },
        timeout=60,
    )
    result = response.json()
    if result.get("IsErroredOnProcessing"):
        raise RuntimeError(result.get("ErrorMessage", "OCR xatosi"))
    lines_out = []
    for parsed in result.get("ParsedResults", []):
        overlay = parsed.get("TextOverlay", {})
        for line in overlay.get("Lines", []):
            words = line.get("Words", [])
            if not words:
                continue
            text = line.get("LineText", "").strip()
            if not text:
                continue
            x0 = min(w["Left"] for w in words)
            y0 = min(w["Top"] for w in words)
            x1 = max(w["Left"] + w["Width"] for w in words)
            y1 = max(w["Top"] + w["Height"] for w in words)
            lines_out.append((text, x0, y0, x1, y1))
    return lines_out
