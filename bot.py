import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes



TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")
    
WEBAPP_URL = "https://montanaqxq.github.io/telegram-timer/?v=2"


def load_config():
    try:
        with open("config.json") as f:
            return json.load(f)
    except:
        return {"target": "2026-04-30 19:00"}


def save_config(data):
    with open("config.json", "w") as f:
        json.dump(data, f)

def plural(n, forms):
    n = abs(n) % 100
    n1 = n % 10

    if 10 < n < 20:
        return forms[2]

    if 1 < n1 < 5:
        return forms[1]

    if n1 == 1:
        return forms[0]

    return forms[2]

def get_remaining():

    data = load_config()
    target = datetime.strptime(data["target"], "%Y-%m-%d %H:%M")
    now = datetime.now()

    delta = target - now

    if delta.total_seconds() <= 0:
        return "Время наступило!"

    days = delta.days
    seconds = delta.seconds

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    return (
        f"⏳ Осталось "
        f"{days} {plural(days, ['день','дня','дней'])} "
        f"{hours} {plural(hours, ['час','часа','часов'])} "
        f"{minutes} {plural(minutes, ['минута','минуты','минут'])}"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_type = update.effective_chat.type

    if chat_type == "private":

        keyboard = [
            [
                InlineKeyboardButton(
                    "⏳ Открыть таймер",
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )
            ]
        ]

        await update.message.reply_text(
            "Бот таймера\n\n"
            "/time — сколько осталось\n"
            "/app — открыть таймер",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    else:

        await update.message.reply_text(
            "Таймер доступен в личном чате с ботом.\n"
            "Напишите боту в личку."
        )


async def show_time(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(get_remaining())


async def open_app(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_type = update.effective_chat.type

    if chat_type == "private":

        keyboard = [
            [
                InlineKeyboardButton(
                    "⏳ Открыть таймер",
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )
            ]
        ]

    else:

        keyboard = [
            [
                InlineKeyboardButton(
                    "⏳ Открыть таймер",
                    url=WEBAPP_URL
                )
            ]
        ]

    await update.message.reply_text(
        "⏳ Таймер события",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("time", show_time))
app.add_handler(CommandHandler("app", open_app))


async def error_handler(update, context):
    print(context.error)


app.add_error_handler(error_handler)

app.add_error_handler(error_handler)

import asyncio

async def main():
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
