import logging
import os
from datetime import time
from zoneinfo import ZoneInfo

import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL_BASE = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = "/telegram-webhook"
BITUNIX_FOOTER = "Powered by Bitunix — trade futures and get bonuses."

if not TELEGRAM_TOKEN:
    raise RuntimeError("Chýba TELEGRAM_BOT_TOKEN")

if not WEBHOOK_URL_BASE:
    raise RuntimeError("Chýba WEBHOOK_URL")

WEBHOOK_URL_BASE = WEBHOOK_URL_BASE.rstrip("/")
FULL_WEBHOOK_URL = WEBHOOK_URL_BASE + WEBHOOK_PATH
SUBSCRIBERS = set()

def add_footer(text): return text.rstrip() + "\n\n" + BITUNIX_FOOTER

def get_market_hours_text():
    return (
        "📈 *Market hours*\n\n"
        "NYSE: 09:30 – 16:00 (ET)\n"
        "LSE: 08:00 – 16:30 (UK time)\n"
    )

def get_fear_greed_text():
    try:
        data = requests.get("https://api.alternative.me/fng/?limit=1&format=json").json()["data"][0]
        return f"😨 *Fear & Greed Index*\nHodnota: *{data['value']}* ({data['value_classification']})"
    except:
        return "😨 Index sa nepodarilo načítať."

def build_daily_message(): return get_market_hours_text() + "\n" + get_fear_greed_text()

async def start(update, context):
    SUBSCRIBERS.add(update.effective_chat.id)
    await update.message.reply_text(add_footer("Prihlásené na denné správy."), parse_mode="Markdown")

async def stop(update, context):
    SUBSCRIBERS.discard(update.effective_chat.id)
    await update.message.reply_text(add_footer("Odhlásené."))

async def now(update, context):
    await update.message.reply_text(add_footer(build_daily_message()), parse_mode="Markdown")

async def daily_job(context):
    if not SUBSCRIBERS: return
    msg = add_footer(build_daily_message())
    for chat in SUBSCRIBERS:
        try: await context.bot.send_message(chat, msg, parse_mode="Markdown")
        except: pass

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("now", now))

    tz = ZoneInfo("Europe/Bratislava")
    app.job_queue.run_daily(daily_job, time=time(8, 0, tzinfo=tz))

    port = int(os.environ.get("PORT", "10000"))
    app.run_webhook(
        listen="0.0.0.0", port=port,
        url_path=WEBHOOK_PATH[1:], webhook_url=FULL_WEBHOOK_URL
    )

if __name__ == "__main__": main()
