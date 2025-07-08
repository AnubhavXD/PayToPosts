import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import logging

# Hardcoded bot token, channel ID, and base URL
TOKEN = "7789956834:AAG4FYY5mV8Qgytw_ZRBR0_O---Zbqz4438"
CHANNEL_ID = "@paytoposts"
BASE_URL = "https://intensive-esther-animeharbour-95b7971a.koyeb.app"

# Prices in USDT
PRICES = {
    "text": 0.10,
    "image": 7.00,
    "voice": 0.50,
    "gif": 7.00,
    "video": 1.00,
    "sticker": 7.00
}

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Telegram bot application
bot_app = Application.builder().token(TOKEN).build()

# Command handler: /start
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

# Callback for payment method selection
async def payment_method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.split("_")[1].upper()
    context.user_data["payment_method"] = method
    await query.edit_message_text(f"You selected *{method}* as your payment method.\nNow send the content you want to post.", parse_mode="Markdown")

# Simulated payment + forward logic
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

# Handle confirmations
async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = context.user_data.get("pending_content")

    if not data:
        await query.edit_message_text("No pending content to confirm.")
        return

    if query.data == "confirm_post":
        await query.edit_message_text("✅ Posting your content...")
        await simulate_payment_and_forward(update, context, data["type"], data)
    else:
        await query.edit_message_text("❌ Post cancelled.")

    context.user_data.pop("pending_content", None)

# Preview handler generator
async def preview_content(update: Update, context: ContextTypes.DEFAULT_TYPE, content_type: str, data: dict, preview_text: str):
    context.user_data["pending_content"] = {"type": content_type, **data}
    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data="confirm_post")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_post")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(preview_text, reply_markup=reply_markup, parse_mode="Markdown")

# Message Handlers
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    cost = round(len(text) * PRICES["text"], 2)
    await preview_content(
    update,
    context,
    "text",
    {"text": text},
    f"📝 *Preview:*\n{text}"
)


{text}

_Price: ${cost}_")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.photo[-1].file_id
    await preview_content(update, context, "photo", {"file_id": file_id}, f"🖼️ *Preview: Image*

_Price: ${PRICES['image']}_")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.video.file_id
    duration = update.message.video.duration
    cost = max(5.0, duration * PRICES["video"])
    await preview_content(update, context, "video", {"file_id": file_id, "duration": duration}, f"🎥 *Preview: Video*

_Duration: {duration}s_
_Price: ${round(cost, 2)}_")

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.sticker.file_id
    await preview_content(update, context, "sticker", {"file_id": file_id}, f"🔖 *Preview: Sticker*

_Price: ${PRICES['sticker']}_")

# Health check route for Koyeb
@app.route("/")
def index():
    return "Bot is alive!"

# Webhook receiver
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.update_queue.put_nowait(update)
    return "OK"

# Add all handlers
def setup_bot():
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CallbackQueryHandler(payment_method_selected, pattern="^pay_"))
    bot_app.add_handler(CallbackQueryHandler(handle_confirmation, pattern="^(confirm_post|cancel_post)$"))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    bot_app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    bot_app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))

# Set webhook after app is ready
async def post_init(app: Application):
    await app.bot.set_webhook(url=f"{BASE_URL}/{TOKEN}")
    logger.info("Webhook has been set.")

# Main entry
if __name__ == "__main__":
    import threading
    import asyncio

    setup_bot()

    async def start_bot():
        await bot_app.initialize()
        await post_init(bot_app)
        await bot_app.start()
        await bot_app.updater.start_polling()
        await bot_app.updater.wait_until_closed()

    def run_flask():
        app.run(host="0.0.0.0", port=8000)

    threading.Thread(target=run_flask).start()
    asyncio.run(start_bot())
