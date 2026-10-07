import json
import logging
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from telegram import (
    BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp,
    Update, WebAppInfo,
)
from telegram.constants import ChatType
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / 'config.json'
DEFAULT_WEBAPP_URL = 'https://montanaqxq.github.io/telegram-timer/?v=20261230'
logger = logging.getLogger(__name__)


def load_config():
    with CONFIG_PATH.open(encoding='utf-8') as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError('config.json должен содержать объект')
    target = datetime.fromisoformat(data['target'])
    if target.tzinfo is None:
        raise ValueError('В target нужно указать часовой пояс, например +03:00')
    ZoneInfo(data['timezone'])
    return data


def get_target(config):
    return datetime.fromisoformat(config['target']).astimezone(ZoneInfo(config['timezone']))


def target_label(config):
    return get_target(config).strftime('%d.%m.%Y, %H:%M') + ' (МСК)'


def load_token():
    token = os.getenv('BOT_TOKEN', '').strip()
    token_path = BASE_DIR / '.bot-token'
    if not token and token_path.is_file():
        token = token_path.read_text(encoding='utf-8').strip()
    if not token:
        raise ValueError('Задайте BOT_TOKEN или сохраните токен в локальном файле .bot-token')
    return token


def webapp_url():
    url = os.getenv('WEBAPP_URL', DEFAULT_WEBAPP_URL).strip()
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.netloc:
        raise ValueError('WEBAPP_URL должен быть публичным HTTPS-адресом страницы таймера')
    return url


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


def get_remaining(now=None, config=None):
    config = load_config() if config is None else config
    target = get_target(config)
    now = datetime.now(target.tzinfo) if now is None else now
    if now.tzinfo is None:
        raise ValueError('Текущее время должно включать часовой пояс')
    duration = (target - now).total_seconds()
    if duration <= 0:
        return '🎉 Время наступило!'
    remaining = int(duration)
    if remaining == 0:
        return '⏳ Осталось меньше секунды'
    days, seconds = divmod(remaining, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if remaining < 60:
        return f'⏳ Осталось {seconds} {plural(seconds, ["секунда", "секунды", "секунд"])}'
    return (
        f'⏳ Осталось {days} {plural(days, ["день", "дня", "дней"])} '
        f'{hours} {plural(hours, ["час", "часа", "часов"])} '
        f'{minutes} {plural(minutes, ["минута", "минуты", "минут"])}'
    )


async def timer_keyboard(update, context):
    if update.effective_chat.type == ChatType.PRIVATE:
        button = InlineKeyboardButton('⏳ Открыть таймер', web_app=WebAppInfo(url=webapp_url()))
        via_private_chat = False
    else:
        # Refresh getMe so enabling the Main Mini App requires no bot restart.
        bot = await context.bot.get_me()
        if bot.has_main_web_app:
            url = f'https://t.me/{bot.username}?startapp=timer'
            via_private_chat = False
        else:
            url = f'https://t.me/{bot.username}?start=timer'
            via_private_chat = True
        button = InlineKeyboardButton('⏳ Открыть таймер', url=url)
    return InlineKeyboardMarkup([[button]]), via_private_chat


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message is None or update.effective_chat is None:
        return
    config = load_config()
    keyboard, via_private_chat = await timer_keyboard(update, context)
    text = (
        f'⏳ Таймер до {target_label(config)}\n\n'
        '/time — сколько осталось\n'
        '/app — открыть таймер'
    )
    if update.effective_chat.type != ChatType.PRIVATE:
        text += f'\n\nВ группе: /time@{context.bot.username} и /app@{context.bot.username}'
    if via_private_chat:
        text += '\n\nКнопка откроет личный чат с ботом, где можно запустить таймер.'
    await update.effective_message.reply_text(text, reply_markup=keyboard)


async def show_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message is None:
        return
    config = load_config()
    await update.effective_message.reply_text(
        get_remaining(config=config) + f'\nДо {target_label(config)}'
    )


async def open_app(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message is None or update.effective_chat is None:
        return
    keyboard, via_private_chat = await timer_keyboard(update, context)
    text = f'⏳ Таймер до {target_label(load_config())}'
    if via_private_chat:
        text += '\nКнопка откроет личный чат с ботом, где можно запустить таймер.'
    await update.effective_message.reply_text(text, reply_markup=keyboard)


async def setup_bot(application: Application):
    await application.bot.set_my_commands([
        BotCommand('start', 'Открыть таймер и список команд'),
        BotCommand('time', 'Сколько осталось до события'),
        BotCommand('app', 'Открыть приложение с таймером'),
    ])
    await application.bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(text='Таймер', web_app=WebAppInfo(url=webapp_url()))
    )
    logger.info('Бот @%s запущен. Отсчёт до %s', application.bot.username, target_label(load_config()))
    if not application.bot.bot.has_main_web_app:
        logger.warning('Главное мини-приложение не настроено: кнопка в группе откроет личный чат.')


async def error_handler(update, context):
    # HTTP exception text may contain the token as part of a request URL.
    safe_message = str(context.error).replace(context.bot.token, '<REDACTED>')
    logger.error('Ошибка %s: %s', type(context.error).__name__, safe_message)


def build_application():
    load_config()
    webapp_url()
    application = ApplicationBuilder().token(load_token()).post_init(setup_bot).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('time', show_time))
    application.add_handler(CommandHandler('app', open_app))
    application.add_error_handler(error_handler)
    return application


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    # run_polling removes the old webhook; queued commands are preserved.
    try:
        build_application().run_polling(drop_pending_updates=False, allowed_updates=['message'])
    except Exception as error:
        token = os.getenv('BOT_TOKEN', '').strip()
        token_file = BASE_DIR / '.bot-token'
        if not token and token_file.is_file():
            token = token_file.read_text(encoding='utf-8').strip()
        safe_message = str(error).replace(token, '<REDACTED>') if token else str(error)
        logger.error('Бот не запущен: %s: %s', type(error).__name__, safe_message)
        raise SystemExit(1)
