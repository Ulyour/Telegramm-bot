
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
VISA_CARD = os.getenv("VISA_CARD")
TON_ADDRESS = os.getenv("TON_ADDRESS")

pending_users = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я продаю доступ в приватный канал.\nНапиши /buy чтобы начать.")

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("1 месяц — 300₽", callback_data="buy_1m")],
        [InlineKeyboardButton("3 месяца — 800₽", callback_data="buy_3m")]
    ]
    await update.message.reply_text("Выбери тариф:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    plan = query.data
    pending_users[user_id] = plan

    # Выбор способа оплаты
    pay_keyboard = [
        [InlineKeyboardButton("Visa", callback_data="pay_visa")],
        [InlineKeyboardButton("USDT (TON Space)", callback_data="pay_usdt")],
        [InlineKeyboardButton("TON", callback_data="pay_ton")]
    ]
    await query.message.reply_text("Выбери способ оплаты:", reply_markup=InlineKeyboardMarkup(pay_keyboard))

async def pay_method_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    method = query.data
    plan = pending_users.get(user_id, "неизвестен")

    if method == "pay_visa":
        text = f"Переведи {'300₽' if plan == 'buy_1m' else '800₽'} на карту:

{VISA_CARD}"
    else:
        crypto = "USDT (TON Space)" if method == "pay_usdt" else "TON"
        text = f"Переведи {'300₽' if plan == 'buy_1m' else '800₽'} в {crypto} на адрес:

{TON_ADDRESS}"

    text += "

После оплаты пришли сюда скриншот или фото чека."

    await query.message.reply_text(text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in pending_users:
        await update.message.reply_text("Сначала выбери тариф через /buy.")
        return

    plan = pending_users[user_id]
    caption = f"❗ Новый платёж от @{update.message.from_user.username or user_id}\nuser_id: {user_id}\nТариф: {plan}"
    photo = update.message.photo[-1].file_id
    await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo, caption=caption)

    await update.message.reply_text("Спасибо! Чек отправлен администратору. Ожидай подтверждения.")

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) != 1:
        await update.message.reply_text("Используй: /confirm <user_id>")
        return

    user_id = int(context.args[0])
    link = await context.bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)

    await context.bot.send_message(chat_id=user_id,
        text=f"Платёж подтверждён! Вот твоя ссылка:\n{link.invite_link}")
    await update.message.reply_text("Пользователь получил ссылку.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("confirm", confirm))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(pay_method_handler, pattern="^pay_"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == "__main__":
    main()
