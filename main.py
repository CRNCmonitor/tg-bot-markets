import logging
import os
from datetime import time
from zoneinfo import ZoneInfo

import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL_BASE = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = "/telegram-webhook"
BITUNIX_FOOTER = "Powered by Bitunix — trade futures and get bonuses."

if not TELEGRAM_TOKEN:
    raise RuntimeError("Chýba env premenná TELEGRAM_BOT_TOKEN")

if not WEBHOOK_URL_BASE:
    raise RuntimeError("Chýba env premenná WEBHOOK_URL")

WEBHOOK_URL_BASE = WEBHOOK_URL_BASE.rstrip("/")
FULL_WEBHOOK_URL = WEBHOOK_URL_BASE + WEBHOOK_PATH

SUBSCRIBERS = set()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

def add_footer(text: str) -> str:
    return text.rstrip() + "\n\n" + BITUNIX_FOOTER

def get_market_hours_text() -> str:
    return (
        "📈 *Market hours*\n\n"
        "NYSE (New York): 09:30 – 16:00 (ET)\n"
        "LSE  (London):   08:00 – 16:30 (UK time)\n"
    )

def get_fear_greed_text() -> str:
    url = "https://api.alternative.me/fng/?limit=1&format=json"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])[0]
        value = data.get("value")
        classification = data.get("value_classification")
        timestamp = data.get("timestamp")
        return (
            "😨 *Crypto Fear & Greed Index*\n"
            f"Aktuálna hodnota: *{value}* ({classification})\n"
            f"Timestamp: {timestamp}\n"
            "Zdroj: alternative.me"
        )
    except Exception:
        return (
            "😨 *Crypto Fear & Greed Index*\n"
            "Index sa teraz nepodarilo načítať.\n"
            "Zdroj: alternative.me"
        )

def build_daily_message() -> str:
    return "\n".join([
        get_market_hours_text(),
        "",
        get_fear_greed_text()
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    SUBSCRIBERS.add(chat_id)
    text = (
        "Ahoj! 🔔\n"
        "Budem ti každý deň posielať:\n"
        "• NYSE & LSE otváracie časy\n"
        "• Crypto Fear & Greed Index\n\n"
        "Príkazy:\n"
        "/stop – odhlásiť\n"
        "/now – okamžité info"
    )
    await update.message.reply_text(add_footer(text), parse_mode="Markdown")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    SUBSCRIBERS.discard(update.effective_chat.id)
    await update.message.reply_text(add_footer("Odhlásené."))

async def now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(add_footer(build_daily_message()), parse_mode="Markdown")

async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    if not SUBSCRIBERS:
        return
    msg = add_footer(build_daily_message())
    for chat_id in list(SUBSCRIBERS):
        try:
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
        except Exception as e:
            logger.warning("Chyba posielania: %s", e)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("now", now))

    tz = ZoneInfo("Europe/Bratislava")
    app.job_queue.run_daily(daily_job, time=time(8, 0, tzinfo=tz))

    port = int(os.environ.get("PORT", "10000"))
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=WEBHOOK_PATH.lstrip("/"),
        webhook_url=FULL_WEBHOOK_URL,
    )

if __name__ == "__main__":
    main()
