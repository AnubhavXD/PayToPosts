# main.py
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import logging

# --- CONFIG --- (HARD-CODED for repo use; replace with your actual values)
TOKEN = "7789956834:AAG4FYY5mV8Qgytw_ZRBR0_O---Zbqz4438"
CHANNEL_ID = "@paytoposts"  # e.g., "@yourchannel" or channel ID as int
BASE_URL = "https://intensive-esther-animeharbour-95b7971a.koyeb.app"  # no trailing slash

# --- PRICING ---
PRICES = {
    "text": 0.10,        # per character
    "image": 7.00,
    "voice": 0.50,       # per second
    "gif": 7.00,
    "video": 1.00,       # per second (min $5.00)
    "sticker": 7.00
}

logging.basicConfig(level=logging.INFO)

# --- Flask health check ---
app = Flask(__name__)
@app.route("/")
def home():
    return "Bot is alive!"

# --- Bot application ---
bot_app = Application.builder().token(TOKEN).build()

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "\U0001F916 *Welcome to PayToPosts Bot!*\n\n"
        "Send content & pay in *USDT* or *Telegram Stars* before it's posted in the channel.\n\n"
        "*Pricing:*\n"
        "- Text: $0.10/char\n"
        "- Image: $7.00\n"
        "- Voice: $0.50/sec\n"
        "- GIF: $7.00\n"
        "- Video: $1.00/sec (min $5.00)\n"
        "- Sticker: $7.00\n\n"
        "Choose a payment method:"
    )
    keyboard = [
        [InlineKeyboardButton("Pay with USDT", callback_data="pay_usdt")],
        [InlineKeyboardButton("Pay with Stars", callback_data="pay_stars")]
    ]
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def payment_method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.split("_")[1].upper()
    context.user_data["payment_method"] = method
    await query.edit_message_text(
        f"You selected *{method}* as your payment method.\nNow send the content you want to post.",
        parse_mode="Markdown"
    )

async def simulate_payment_and_forward(update: Update, context: ContextTypes.DEFAULT_TYPE, content_type: str, data: dict):
    user = update.effective_user
    username = user.username or user.first_name
    method = context.user_data.get("payment_method", "USDT")

    if content_type == "text":
        text = data["text"]
        cost = round(len(text) * PRICES["text"], 2)
        msg = f"\U0001F4AC *Text Post from @{username}*\nPaid: ${cost} ({method})\n\n{text}"
        await context.bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="Markdown")

    elif content_type == "photo":
        cost = PRICES["image"]
        await context.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=data["file_id"],
            caption=f"Image from @{username} (${cost} via {method})"
        )

    elif content_type == "video":
        duration = data["duration"]
        cost = max(5.0, duration * PRICES["video"])
        await context.bot.send_video(
            chat_id=CHANNEL_ID,
            video=data["file_id"],
            caption=f"Video from @{username} (${round(cost, 2)} via {method})"
        )

    elif content_type == "sticker":
        cost = PRICES["sticker"]
        await context.bot.send_sticker(chat_id=CHANNEL_ID, sticker=data["file_id"])
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"Sticker from @{username} (${cost} via {method})")

# --- Content Handlers ---
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

# --- Webhook route (for Telegram) ---
@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.update_queue.put_nowait(update)
    return "OK"

# --- Register Handlers ---
def setup_bot():
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CallbackQueryHandler(payment_method_selected))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    bot_app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    bot_app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))

# --- MAIN ENTRYPOINT ---
if __name__ == "__main__":
    setup_bot()
    bot_app.run_webhook(
        listen="0.0.0.0",
        port=8000,
        webhook_path=f"/{TOKEN}",
        webhook_url=f"{BASE_URL}/{TOKEN}"
    )
