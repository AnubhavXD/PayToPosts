import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)

# Telegram Bot Token and Channel ID
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@yourchannel")

# Prices in USDT
PRICES = {
    "text": 0.10,        # per character
    "image": 7.00,
    "voice": 0.50,       # per second
    "gif": 7.00,
    "video": 1.00,       # per second (min 5 USDT)
    "sticker": 7.00,
}

# Dummy currency conversion: 1 Star = $0.01
def usdt_to_stars(usdt):
    return int(usdt / 0.01)

# Util: Get user's @username or full name
def get_user_mention(user):
    return f"@{user.username}" if user.username else user.full_name

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Send any message or media to post it after simulated payment via Stars 💫 or USDT.")

# Simulated payment preview
async def request_payment(update, context, media_type, details, preview_fn):
    cost_usdt = details.get("cost", 0)
    cost_stars = usdt_to_stars(cost_usdt)
    user = update.effective_user
    username = get_user_mention(user)

    msg = (
        f"{username}, to post your {media_type}, you need to pay:\n\n"
        f"💫 {cost_stars} Stars (simulated)\n"
        f"💰 Or {cost_usdt:.2f} USDT (dummy)\n\n"
        f"✅ Proceeding with simulated payment..."
    )

    await update.message.reply_text(msg)
    await preview_fn()

# TEXT
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    cost = len(text) * PRICES["text"]

    async def post():
        user = update.effective_user
        stars = usdt_to_stars(cost)
        mention = get_user_mention(user)
        formatted = f"{mention} paid {stars} ⭐️\n{text}"
        await context.bot.send_message(chat_id=CHANNEL_ID, text=formatted)
        await update.message.reply_text("✅ Your message has been posted!")

    await request_payment(update, context, "text", {"text": text, "cost": cost}, post)

# IMAGE
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1].file_id
    caption = update.message.caption or ""
    cost = PRICES["image"]

    async def post():
        mention = get_user_mention(update.effective_user)
        stars = usdt_to_stars(cost)
        text = f"{mention} paid {stars} ⭐️\n{caption}"
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=photo, caption=text)
        await update.message.reply_text("✅ Your image has been posted!")

    await request_payment(update, context, "image", {"cost": cost}, post)

# GIF
async def handle_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gif = update.message.animation.file_id
    caption = update.message.caption or ""
    cost = PRICES["gif"]

    async def post():
        mention = get_user_mention(update.effective_user)
        stars = usdt_to_stars(cost)
        text = f"{mention} paid {stars} ⭐️\n{caption}"
        await context.bot.send_animation(chat_id=CHANNEL_ID, animation=gif, caption=text)
        await update.message.reply_text("✅ Your GIF has been posted!")

    await request_payment(update, context, "gif", {"cost": cost}, post)

# VOICE
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    duration = voice.duration
    cost = duration * PRICES["voice"]

    async def post():
        mention = get_user_mention(update.effective_user)
        stars = usdt_to_stars(cost)
        caption = f"{mention} paid {stars} ⭐️ (Voice: {duration}s)"
        await context.bot.send_voice(chat_id=CHANNEL_ID, voice=voice.file_id, caption=caption)
        await update.message.reply_text("✅ Your voice note has been posted!")

    await request_payment(update, context, "voice note", {"cost": cost}, post)

# VIDEO
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video
    duration = video.duration
    cost = max(5.00, duration * PRICES["video"])

    async def post():
        mention = get_user_mention(update.effective_user)
        stars = usdt_to_stars(cost)
        caption = f"{mention} paid {stars} ⭐️ (Video: {duration}s)\n{update.message.caption or ''}"
        await context.bot.send_video(chat_id=CHANNEL_ID, video=video.file_id, caption=caption)
        await update.message.reply_text("✅ Your video has been posted!")

    await request_payment(update, context, "video", {"cost": cost}, post)

# STICKER
async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sticker = update.message.sticker
    cost = PRICES["sticker"]

    async def post():
        mention = get_user_mention(update.effective_user)
        stars = usdt_to_stars(cost)
        caption = f"{mention} paid {stars} ⭐️ (Sticker)"
        await context.bot.send_sticker(chat_id=CHANNEL_ID, sticker=sticker.file_id)
        await context.bot.send_message(chat_id=CHANNEL_ID, text=caption)
        await update.message.reply_text("✅ Your sticker has been posted!")

    await request_payment(update, context, "sticker", {"cost": cost}, post)

# Dummy Flask server for Koyeb
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    flask_app.run(host="0.0.0.0", port=8000)

# Main function
def main():
    # Start Flask server
    threading.Thread(target=run_flask).start()

    # Start Telegram bot
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.ANIMATION, handle_gif))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))

    print("🚀 Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
