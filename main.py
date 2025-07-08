import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MessageEntity
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

# Bot and channel setup
TOKEN = "7789956834:AAG4FYY5mV8Qgytw_ZRBR0_O---Zbqz4438"
CHANNEL_ID = "@paytoposts"

# Pricing in USDT
PRICES = {
    "text": 0.10,         # per character
    "image": 7.00,        # per image
    "voice": 0.50,        # per second
    "gif": 7.00,          # per gif
    "video": 1.00,        # per second, min 5
    "sticker": 7.00       # per sticker
}

# USDT to Stars conversion (1 Star = 0.01 USDT)
def usdt_to_stars(usdt_amount):
    return int(usdt_amount / 0.01)

# Get user mention
def get_user_mention(user):
    return f"@{user.username}" if user.username else user.full_name

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to PayToPosts!\nSend a message or media and you'll be asked to pay with Stars ⭐️ to post it to the world! ( @PayToPosts )"
    )

# --- Handlers for Incoming Content ---

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    cost = len(text) * PRICES["text"]
    stars = usdt_to_stars(cost)

    context.user_data["pending"] = {
        "type": "text",
        "content": text,
        "cost": stars,
        "user": get_user_mention(user)
    }

    await update.message.reply_text(
        f"📝 This text costs {stars} ⭐️.\nDo you want to post it?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Pay with Stars", callback_data="pay")]])
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    photo_id = update.message.photo[-1].file_id
    caption = update.message.caption or ""
    stars = usdt_to_stars(PRICES["image"])

    context.user_data["pending"] = {
        "type": "photo",
        "file": photo_id,
        "caption": caption,
        "cost": stars,
        "user": get_user_mention(user)
    }

    await update.message.reply_text(
        f"🖼️ This image costs {stars} ⭐️.\nDo you want to post it?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Pay with Stars", callback_data="pay")]])
    )

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    voice = update.message.voice
    stars = usdt_to_stars(voice.duration * PRICES["voice"])

    context.user_data["pending"] = {
        "type": "voice",
        "file": voice.file_id,
        "duration": voice.duration,
        "cost": stars,
        "user": get_user_mention(user)
    }

    await update.message.reply_text(
        f"🎙️ This voice note ({voice.duration}s) costs {stars} ⭐️.\nDo you want to post it?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Pay with Stars", callback_data="pay")]])
    )

async def handle_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    gif_id = update.message.animation.file_id
    caption = update.message.caption or ""
    stars = usdt_to_stars(PRICES["gif"])

    context.user_data["pending"] = {
        "type": "gif",
        "file": gif_id,
        "caption": caption,
        "cost": stars,
        "user": get_user_mention(user)
    }

    await update.message.reply_text(
        f"🎞️ This GIF costs {stars} ⭐️.\nDo you want to post it?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Pay with Stars", callback_data="pay")]])
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    video = update.message.video
    cost_usdt = max(5.0, video.duration * PRICES["video"])
    stars = usdt_to_stars(cost_usdt)

    context.user_data["pending"] = {
        "type": "video",
        "file": video.file_id,
        "duration": video.duration,
        "caption": update.message.caption or "",
        "cost": stars,
        "user": get_user_mention(user)
    }

    await update.message.reply_text(
        f"🎥 This video ({video.duration}s) costs {stars} ⭐️.\nDo you want to post it?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Pay with Stars", callback_data="pay")]])
    )

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    stars = usdt_to_stars(PRICES["sticker"])

    context.user_data["pending"] = {
        "type": "sticker",
        "file": update.message.sticker.file_id,
        "cost": stars,
        "user": get_user_mention(user)
    }

    await update.message.reply_text(
        f"🧸 This sticker costs {stars} ⭐️.\nDo you want to post it?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Pay with Stars", callback_data="pay")]])
    )

# --- Callback: Simulated Payment ---
async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = context.user_data.get("pending")
    if not data:
        await query.edit_message_text("❌ No pending post found.")
        return

    kind = data["type"]
    user = data["user"]
    stars = data["cost"]

    if kind == "text":
        caption = f"{user} paid {stars} ⭐️\n\n{data['content']}"
        await context.bot.send_message(CHANNEL_ID, text=caption)

    elif kind == "photo":
        caption = f"{user} paid {stars} ⭐️\n\n{data['caption']}"
        await context.bot.send_photo(CHANNEL_ID, photo=data["file"], caption=caption)

    elif kind == "voice":
        caption = f"{user} paid {stars} ⭐️ (Voice: {data['duration']}s)"
        await context.bot.send_voice(CHANNEL_ID, voice=data["file"], caption=caption)

    elif kind == "gif":
        caption = f"{user} paid {stars} ⭐️\n\n{data['caption']}"
        await context.bot.send_animation(CHANNEL_ID, animation=data["file"], caption=caption)

    elif kind == "video":
        caption = f"{user} paid {stars} ⭐️ (Video: {data['duration']}s)\n\n{data['caption']}"
        await context.bot.send_video(CHANNEL_ID, video=data["file"], caption=caption)

    elif kind == "sticker":
        await context.bot.send_sticker(CHANNEL_ID, sticker=data["file"])
        await context.bot.send_message(CHANNEL_ID, text=f"{user} paid {stars} ⭐️ (Sticker)")

    await query.edit_message_text("✅ Payment confirmed! Your post has been published.")

# --- Main ---
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.ANIMATION, handle_gif))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    app.add_handler(CallbackQueryHandler(handle_payment, pattern="^pay$"))

    print("🚀 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
