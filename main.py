import os
import logging
import asyncio
import nest_asyncio  # ✅ Helps avoid "event loop closed" error
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler
)

# Apply nested asyncio support
nest_asyncio.apply()

# Bot Configuration
TOKEN = os.getenv("BOT_TOKEN", "7789956834:AAG4FYY5mV8Qgytw_ZRBR0_O---Zbqz4438")
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

# Flask App
app = Flask(__name__)
loop = asyncio.get_event_loop()
bot_app = Application.builder().token(TOKEN).concurrent_updates(True).build()
user_state = {}
user_preview_cache = {}

# ------------------ Bot Handlers ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_state[user_id] = "awaiting_payment"
    keyboard = [[
        InlineKeyboardButton("💳 Pay with USDT", callback_data="pay_usdt"),
        InlineKeyboardButton("🌟 Pay with Stars", callback_data="pay_stars")
    ]]
    text = (
        "🤖 *Welcome to PayToPosts Bot!*\n\n"
        "Please choose a payment method to begin posting content.\n"
        "- Text: $0.10/character\n"
        "- Image/GIF/Sticker: $7.00\n"
        "- Voice: $0.50/sec\n"
        "- Video: $1.00/sec (Min $5)\n\n"
        "_This is a simulated payment flow._"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def payment_method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    method = query.data.split("_")[1].upper()
    user_state[user_id] = "awaiting_content"
    context.user_data["payment_method"] = method
    await query.edit_message_text(f"✅ *{method} selected.* Now send your content (text/photo/video/etc).", parse_mode="Markdown")

async def preview_content(update, context, content_type, data, caption):
    user_id = update.effective_user.id
    if user_state.get(user_id) != "awaiting_content":
        return
    user_preview_cache[user_id] = (content_type, data, context.user_data.get("payment_method", "USDT"))
    keyboard = [[
        InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
        InlineKeyboardButton("❌ Cancel", callback_data="cancel")
    ]]
    markup = InlineKeyboardMarkup(keyboard)
    if content_type == "text":
        await update.message.reply_text(caption, reply_markup=markup, parse_mode="Markdown")
    elif content_type == "photo":
        await update.message.reply_photo(photo=data["file_id"], caption=caption, reply_markup=markup)
    elif content_type == "video":
        await update.message.reply_video(video=data["file_id"], caption=caption, reply_markup=markup)
    elif content_type == "sticker":
        await update.message.reply_sticker(sticker=data["file_id"])
        await update.message.reply_text(caption, reply_markup=markup)
    elif content_type == "voice":
        await update.message.reply_voice(voice=data["file_id"], caption=caption, reply_markup=markup)
    elif content_type == "gif":
        await update.message.reply_animation(animation=data["file_id"], caption=caption, reply_markup=markup)

async def confirm_or_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "cancel":
        user_preview_cache.pop(user_id, None)
        user_state[user_id] = "awaiting_payment"
        await query.edit_message_text("❌ Canceled.")
        return
    if user_id not in user_preview_cache:
        await query.edit_message_text("⚠️ Nothing to confirm.")
        return
    content_type, data, method = user_preview_cache.pop(user_id)
    username = query.from_user.username or query.from_user.first_name
    if content_type == "text":
        text = data["text"]
        cost = round(len(text) * PRICES["text"], 2)
        msg = f"💬 *Text from @{username}*\nPaid: ${cost} via {method}\n\n{text}"
        await context.bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="Markdown")
    elif content_type == "photo":
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=data["file_id"], caption=f"📸 from @{username} ($7.00 via {method})")
    elif content_type == "video":
        duration = data["duration"]
        cost = max(5.0, duration * PRICES["video"])
        await context.bot.send_video(chat_id=CHANNEL_ID, video=data["file_id"], caption=f"🎥 from @{username} (${round(cost, 2)} via {method})")
    elif content_type == "sticker":
        await context.bot.send_sticker(chat_id=CHANNEL_ID, sticker=data["file_id"])
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"🔖 from @{username} ($7.00 via {method})")
    elif content_type == "voice":
        duration = data["duration"]
        cost = round(duration * PRICES["voice"], 2)
        await context.bot.send_voice(chat_id=CHANNEL_ID, voice=data["file_id"], caption=f"🎙️ from @{username} (${cost} via {method})")
    elif content_type == "gif":
        await context.bot.send_animation(chat_id=CHANNEL_ID, animation=data["file_id"], caption=f"🎞️ from @{username} ($7.00 via {method})")
    await query.edit_message_text("✅ Published!")
    user_state[user_id] = "awaiting_payment"

# ------------------ Message Handlers ------------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await preview_content(update, context, "text", {"text": update.message.text}, f"📝 *Preview:* {update.message.text}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await preview_content(update, context, "photo", {"file_id": update.message.photo[-1].file_id}, "🖼️ *Preview: Image*")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await preview_content(update, context, "video", {"file_id": update.message.video.file_id, "duration": update.message.video.duration}, "🎬 *Preview: Video*")

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await preview_content(update, context, "sticker", {"file_id": update.message.sticker.file_id}, "🔖 *Preview: Sticker*")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await preview_content(update, context, "voice", {"file_id": update.message.voice.file_id, "duration": update.message.voice.duration}, "🎙️ *Preview: Voice Note*")

async def handle_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await preview_content(update, context, "gif", {"file_id": update.message.animation.file_id}, "🎞️ *Preview: GIF*")

# ------------------ Flask Webhook ------------------

@app.route("/")
def index():
    return "✅ Bot is alive!"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    loop.create_task(bot_app.process_update(update))
    return "OK"

# ------------------ Initialization ------------------

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

def main():
    setup_bot()
    loop.run_until_complete(bot_app.initialize())
    loop.run_until_complete(bot_app.bot.set_webhook(url=f"{BASE_URL}/{TOKEN}"))
    loop.run_until_complete(bot_app.start())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


if __name__ == "__main__":
    main()
