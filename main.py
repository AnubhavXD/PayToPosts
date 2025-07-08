import os
import threading
from flask import Flask
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, MessageEntity, InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

# === BOT CONFIG ===
TOKEN = "7789956834:AAG4FYY5mV8Qgytw_ZRBR0_O---Zbqz4438"
CHANNEL_ID = "@paytoposts"

# Pricing (in USDT)
PRICES = {
    "text": 0.10,     # per char
    "image": 7.00,
    "voice": 0.50,    # per second
    "gif": 7.00,
    "video": 1.00,    # per sec, min 5
    "sticker": 7.00
}

# ========== FLASK SERVER ========== #
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot is running", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=8000)

# ========== UTILITIES ========== #
def usdt_to_stars(usdt_amount):
    return int(usdt_amount / 0.01)

def get_user_mention(user):
    return f"@{user.username}" if user.username else user.full_name

# Temporary storage of pending payments
pending_messages = {}

# ========== HANDLERS ========== #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Send a message or media, and I’ll show you the cost in Stars or USDT. Then simulate a payment to post it!")

# ========== PAYMENT SIMULATION ========== #
async def request_payment(update, context, content_type, details, preview_fn):
    user = update.effective_user
    cost = details["cost"]
    stars = usdt_to_stars(cost)
    msg = f"{get_user_mention(user)}, your post costs:\n💸 {cost:.2f} USDT or {stars} ⭐️ Stars\n\nChoose a method to simulate payment:"

    # Store message temporarily
    pending_messages[user.id] = {"type": content_type, "details": details}

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💫 Pay with Stars", callback_data="pay_stars")],
        [InlineKeyboardButton("💸 Pay with USDT (Simulated)", callback_data="pay_crypto")]
    ])

    await preview_fn()
    await update.message.reply_text(msg, reply_markup=keyboard)

# ========== CALLBACKS ========== #
async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    if user.id not in pending_messages:
        await query.edit_message_text("⚠️ No pending message found.")
        return

    data = pending_messages.pop(user.id)
    content_type = data["type"]
    d = data["details"]
    mention = get_user_mention(user)

    caption = f"{mention} paid {usdt_to_stars(d['cost'])} ⭐️ ({content_type.title()})"
    if d.get("extra_caption"):
        caption += f"\n{d['extra_caption']}"

    # Post to channel
    if content_type == "text":
        caption = f"{mention} paid {usdt_to_stars(d['cost'])} ⭐️\n{d['text']}"
        await context.bot.send_message(chat_id=CHANNEL_ID, text=caption)
    elif content_type == "photo":
        await context.bot.send_photo(chat_id=CHANNEL_ID, photo=d["file_id"], caption=caption)
    elif content_type == "voice":
        await context.bot.send_voice(chat_id=CHANNEL_ID, voice=d["file_id"], caption=caption)
    elif content_type == "gif":
        await context.bot.send_animation(chat_id=CHANNEL_ID, animation=d["file_id"], caption=caption)
    elif content_type == "video":
        await context.bot.send_video(chat_id=CHANNEL_ID, video=d["file_id"], caption=caption)
    elif content_type == "sticker":
        await context.bot.send_sticker(chat_id=CHANNEL_ID, sticker=d["file_id"])
        await context.bot.send_message(chat_id=CHANNEL_ID, text=caption)

    await query.edit_message_text("✅ Payment simulated! Your content has been posted.")

# ========== MEDIA HANDLERS ========== #
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    cost = len(text) * PRICES["text"]
    await request_payment(update, context, "text", {"text": text, "cost": cost}, lambda: None)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_id = update.message.photo[-1].file_id
    caption = update.message.caption or ""
    cost = PRICES["image"]
    await request_payment(update, context, "photo", {
        "file_id": photo_id,
        "cost": cost,
        "extra_caption": caption
    }, lambda: None)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    cost = voice.duration * PRICES["voice"]
    await request_payment(update, context, "voice", {
        "file_id": voice.file_id,
        "cost": cost
    }, lambda: None)

async def handle_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gif = update.message.animation
    caption = update.message.caption or ""
    cost = PRICES["gif"]
    await request_payment(update, context, "gif", {
        "file_id": gif.file_id,
        "cost": cost,
        "extra_caption": caption
    }, lambda: None)

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video
    caption = update.message.caption or ""
    cost = max(5.00, video.duration * PRICES["video"])
    await request_payment(update, context, "video", {
        "file_id": video.file_id,
        "cost": cost,
        "extra_caption": caption
    }, lambda: None)

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = update.message.sticker.file_id
    cost = PRICES["sticker"]
    await request_payment(update, context, "sticker", {
        "file_id": file_id,
        "cost": cost
    }, lambda: None)

# ========== RUN ========== #
def run_bot():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.ANIMATION, handle_gif))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))

    print("🤖 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()
