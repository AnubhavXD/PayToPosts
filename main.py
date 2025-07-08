import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import logging
import asyncio
import threading

# Bot Configuration
TOKEN = "7789956834:AAG4FYY5mV8Qgytw_ZRBR0_O---Zbqz4438"
CHANNEL_ID = "@paytoposts"
BASE_URL = "https://intensive-esther-animeharbour-95b7971a.koyeb.app"

PRICES = {
    "text": 0.10,
    "image": 7.00,
    "voice": 0.50,
    "gif": 7.00,
    "video": 1.00,
    "sticker": 7.00
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot_app = Application.builder().token(TOKEN).build()

# Memory cache for previews
user_preview_cache = {}

# /start command
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
    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# Payment method
async def payment_method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.split("_")[1].upper()
    context.user_data["payment_method"] = method
    await query.edit_message_text(f"You selected *{method}* as your payment method.\nNow send the content you want to post.", parse_mode="Markdown")

# Preview content
async def preview_content(update, context, content_type, data, caption):
    user_id = update.effective_user.id
    user_preview_cache[user_id] = (content_type, data, context.user_data.get("payment_method", "USDT"))

    keyboard = [[
        InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
        InlineKeyboardButton("❌ Cancel", callback_data="cancel")
    ]]

    if content_type == "text":
        await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif content_type == "photo":
        await update.message.reply_photo(photo=data["file_id"], caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))
    elif content_type == "video":
        await update.message.reply_video(video=data["file_id"], caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))
    elif content_type == "sticker":
        await update.message.reply_sticker(sticker=data["file_id"])
        await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard))
    elif content_type == "voice":
        await update.message.reply_voice(voice=data["file_id"], caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))
    elif content_type == "gif":
        await update.message.reply_animation(animation=data["file_id"], caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))

# Confirm/Cancel buttons
async def confirm_or_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "cancel":
        user_preview_cache.pop(user_id, None)
        await query.edit_message_text("❌ Post cancelled.")
        return

    if user_id not in user_preview_cache:
        await query.edit_message_text("No pending preview to confirm.")
        return

    content_type, data, method = user_preview_cache.pop(user_id)
    username = query.from_user.username or query.from_user.first_name

    if content_type == "text":
        text = data["text"]
        cost = round(len(text) * PRICES["text"], 2)
        msg = f"💬 *Text Post from @{username}*\nPaid: ${cost} ({method})\n\n{text}"
        await context.bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="Markdown")
    elif content_type == "photo":
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=data["file_id"], caption=f"Image from @{username} ($7.00 paid via {method})")
    elif content_type == "video":
        duration = data["duration"]
        cost = max(5.0, duration * PRICES["video"])
        await context.bot.send_video(chat_id=CHANNEL_ID, video=data["file_id"], caption=f"Video from @{username} ($ {round(cost, 2)} paid via {method})")
    elif content_type == "sticker":
        await context.bot.send_sticker(chat_id=CHANNEL_ID, sticker=data["file_id"])
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"Sticker from @{username} ($7.00 paid via {method})")
    elif content_type == "voice":
        duration = data["duration"]
        cost = round(duration * PRICES["voice"], 2)
        await context.bot.send_voice(chat_id=CHANNEL_ID, voice=data["file_id"], caption=f"Voice note from @{username} (${cost} paid via {method})")
    elif content_type == "gif":
        await context.bot.send_animation(chat_id=CHANNEL_ID, animation=data["file_id"], caption=f"GIF from @{username} ($7.00 paid via {method})")

    await query.edit_message_text("✅ Post confirmed and published!")

# Message handlers with preview
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    caption = f"📝 *Preview:*\n{text}"
    await preview_content(update, context, "text", {"text": text}, caption)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.photo[-1].file_id
    caption = "🖼️ *Preview: Image*"
    await preview_content(update, context, "photo", {"file_id": file_id}, caption)

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.video.file_id
    duration = update.message.video.duration
    caption = "🎬 *Preview: Video*"
    await preview_content(update, context, "video", {"file_id": file_id, "duration": duration}, caption)

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.sticker.file_id
    caption = "🔖 *Preview: Sticker*"
    await preview_content(update, context, "sticker", {"file_id": file_id}, caption)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.voice.file_id
    duration = update.message.voice.duration
    caption = "🎙️ *Preview: Voice Note*"
    await preview_content(update, context, "voice", {"file_id": file_id, "duration": duration}, caption)

async def handle_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.animation.file_id
    caption = "🎞️ *Preview: GIF*"
    await preview_content(update, context, "gif", {"file_id": file_id}, caption)

@app.route("/")
def index():
    return "Bot is alive!"

@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    await bot_app.process_update(update)
    return "OK"

def setup_bot():
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CallbackQueryHandler(payment_method_selected, pattern="^pay_"))
    bot_app.add_handler(CallbackQueryHandler(confirm_or_cancel, pattern="^(confirm|cancel)$"))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    bot_app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    bot_app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    bot_app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    bot_app.add_handler(MessageHandler(filters.ANIMATION, handle_gif))

async def post_init(app: Application):
    await app.bot.set_webhook(url=f"{BASE_URL}/{TOKEN}")
    logger.info("Webhook has been set.")

if __name__ == "__main__":
    setup_bot()

    async def start_bot():
        await bot_app.initialize()
        await post_init(bot_app)
        await bot_app.start()
        # No polling needed

    def run_flask():
        app.run(host="0.0.0.0", port=8000)

    threading.Thread(target=run_flask).start()
    asyncio.run(start_bot())
