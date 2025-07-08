# main.py
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import logging

# ✅ Hardcoded values (be cautious if pushing to GitHub)
TOKEN = "7789956834:AAG4FYY5mV8Qgytw_ZRBR0_O---Zbqz4438"
CHANNEL_ID = "@paytoposts"
BASE_URL = "https://intensive-esther-animeharbour-95b7971a.koyeb.app"

# Prices
PRICES = {
    "text": 0.10,        # per character
    "image": 7.00,
    "voice": 0.50,       # per second
    "gif": 7.00,
    "video": 1.00,       # per second (min $5.00)
    "sticker": 7.00
}

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
bot_app = Application.builder().token(TOKEN).build()

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "\U0001F916 *Welcome to PayToPosts Bot!*\n\n"
        "You can send different types of content and pay in *USDT* or *Telegram Stars* before it's posted in our channel.\n\n"
        "*Pricing:*\n"
        "- Text: $0.10 per character\n"
        "- Image: $7.00 each\n"
        "- Voice Note: $0.50 per second\n"
        "- GIF: $7.00 each\n"
        "- Video: $1.00 per second (minimum $5.00)\n"
        "- Sticker: $7.00 each\n\n"
        "Select a payment method below to continue."
    )
    keyboard = [[
        InlineKeyboardButton("Pay with USDT", callback_data="pay_usdt"),
        InlineKeyboardButton("Pay with Stars", callback_data="pay_stars")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")

# Handle button selection
async def payment_method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.split("_")[1].upper()
    context.user_data["payment_method"] = method
    await query.edit_message_text(f"You selected *{method}* as your payment method.\nNow send the content you want to post.", parse_mode="Markdown")

# Dummy payment simulator
async def simulate_payment_and_forward(update: Update, context: ContextTypes.DEFAULT_TYPE, content_type: str, data: dict):
    user = update.effective_user
    username = user.username or user.first_name
    method = context.user_data.get("payment_method", "USDT")

    if content_type == "text":
        text = data["text"]
        cost = round(len(text) * PRICES["text"], 2)
        message = f"\U0001F4AC *Text Post from @{username}*\nPaid: ${cost} ({method})\n\n{text}"
        await context.bot.send_message(chat_id=CHANNEL_ID, text=message, parse_mode="Markdown")
    elif content_type == "photo":
        cost = PRICES["image"]
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=data["file_id"], caption=f"Image from @{username} ($ {cost} paid via {method})")
    elif content_type == "video":
        cost = max(5.0, data["duration"] * PRICES["video"])
        await context.bot.send_video(chat_id=CHANNEL_ID, video=data["file_id"], caption=f"Video from @{username} ($ {round(cost, 2)} paid via {method})")
    elif content_type == "sticker":
        await context.bot.send_sticker(chat_id=CHANNEL_ID, sticker=data["file_id"])
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"Sticker from @{username} ($7.00 paid via {method})")

# Handlers
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await simulate_payment_and_forward(update, context, "text", {"text": update.message.text})

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.photo[-1].file_id
    await simulate_payment_and_forward(update, context, "photo", {"file_id": file_id})

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.video.file_id
    duration = update.message.video.duration
    await simulate_payment_and_forward(update, context, "video", {"file_id": file_id, "duration": duration})

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.sticker.file_id
    await simulate_payment_and_forward(update, context, "sticker", {"file_id": file_id})

# Health check
@app.route("/")
def index():
    return "Bot is running!"

# Webhook endpoint
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.update_queue.put_nowait(update)
    return "OK"

def setup_bot():
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CallbackQueryHandler(payment_method_selected))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    bot_app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    bot_app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))

if __name__ == '__main__':
    import asyncio
    setup_bot()
    asyncio.run(bot_app.initialize())
    asyncio.run(bot_app.bot.set_webhook(f"{BASE_URL}/{TOKEN}"))
    bot_app.run_webhook(listen="0.0.0.0", port=8000, webhook_path=f"/{TOKEN}")
