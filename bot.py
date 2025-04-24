import os
import threading
import logging
from flask import Flask
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
VISA_CARD = os.getenv("VISA_CARD")
TON_ADDRESS = os.getenv("TON_ADDRESS")

pending_users = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Command /start from user {user_id}")
    await update.message.reply_text(
        "Привет! Я продаю доступ в приватный канал.\nНапиши /buy чтобы начать."
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Command /buy from user {user_id}")
    keyboard = [
        [InlineKeyboardButton("1 месяц — 300₽", callback_data="buy_1m")],
        [InlineKeyboardButton("3 месяца — 800₽", callback_data="buy_3m")]
    ]
    await update.message.reply_text("Выбери тариф:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    plan = query.data
    pending_users[user_id] = plan
    logger.info(f"User {user_id} selected plan {plan}")
    await query.answer()

    pay_keyboard = [
        [InlineKeyboardButton("Visa", callback_data="pay_visa")],
        [InlineKeyboardButton("USDT (TON Space)", callback_data="pay_usdt")],
        [InlineKeyboardButton("TON", callback_data="pay_ton")]
    ]
    await query.message.reply_text("Выбери способ оплаты:", reply_markup=InlineKeyboardMarkup(pay_keyboard))

async def pay_method_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    method = query.data
    plan = pending_users.get(user_id, "неизвестен")
    logger.info(f"User {user_id} selected payment method {method} for plan {plan}")
    await query.answer()

    if method == "pay_visa":
        text = f"Переведи {'300₽' if plan == 'buy_1m' else '800₽'} на карту:\n\n{VISA_CARD}"
    else:
        method_name = "USDT (TON Space)" if method == "pay_usdt" else "TON"
        text = f"Переведи {'300₽' if plan == 'buy_1m' else '800₽'} в {method_name} на адрес:\n\n{TON_ADDRESS}"

    text += "\n\nПосле оплаты пришли сюда скриншот или фото чека."
    await query.message.reply_text(text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    logger.info(f"Received photo from user {user_id}")
    if user_id not in pending_users:
        await update.message.reply_text("Сначала выбери тариф через /buy.")
        return
    plan = pending_users[user_id]
    caption = (
        f"❗ Новый платёж от @{update.message.from_user.username or user_id}\n"
        f"user_id: {user_id}\nТариф: {plan}"
    )
    photo = update.message.photo[-1].file_id
    await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo, caption=caption)
    await update.message.reply_text("Спасибо! Чек отправлен администратору. Ожидай подтверждения.")

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"Admin {user_id} issued confirm with args {context.args}")
    if user_id != ADMIN_ID:
        return
    if len(context.args) != 1:
        await update.message.reply_text("Используй: /confirm <user_id>")
        return
    target_id = int(context.args[0])
    link = await context.bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
    logger.info(f"Generated invite link for user {target_id}")
    await context.bot.send_message(
        chat_id=target_id,
        text=f"Платёж подтверждён! Вот твоя ссылка:\n{link.invite_link}"
    )
    await update.message.reply_text("Пользователь получил ссылку.")

def run_telegram_bot():
    logger.info("Starting Telegram bot polling")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("confirm", confirm))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(pay_method_handler, pattern="^pay_"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

# Flask для порт-биндинга
web_app = Flask(__name__)

@web_app.route("/")
def status():
    return "Bot is running", 200

if __name__ == "__main__":
    # Запускаем Telegram-бота в отдельном потоке
    threading.Thread(target=run_telegram_bot).start()
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting Flask server on port {port}")
    web_app.run(host="0.0.0.0", port=port)