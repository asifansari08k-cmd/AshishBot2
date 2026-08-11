import os
import asyncio
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ================= CONFIGURATION =================
BOT_TOKEN = "7659136250:AAFvUTPqnEKA7XbU5Ga0NLsdWGyqDR7LmIA"
OWNER_ID = 8558656037  # Apni Telegram ID yahan dalein

# ================= MONGODB (DATABASE) SYSTEM =================
MONGO_URL = "mongodb+srv://Elevenyts:Elevenyts@cluster0.vuyc1u2.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
mongo_client = MongoClient(MONGO_URL)
db = mongo_client["telegram_bot_db"]
settings_collection = db["bot_settings"]
saved_media_collection = db["saved_media"]

# Helper functions for Database
def get_setting(key, default=None):
    doc = settings_collection.find_one({"_id": "bot_config"})
    if doc and "settings" in doc:
        return doc["settings"].get(key, default)
    return default

def set_setting(key, value):
    settings_collection.update_one(
        {"_id": "bot_config"},
        {"$set": {f"settings.{key}": value}},
        upsert=True
    )

def get_msg(msg_type):
    doc = settings_collection.find_one({"_id": "bot_config"})
    if doc and "msgs" in doc:
        return doc["msgs"].get(msg_type, {})
    return {}

def set_msg(msg_type, msg_data):
    settings_collection.update_one(
        {"_id": "bot_config"},
        {"$set": {f"msgs.{msg_type}": msg_data}},
        upsert=True
    )

# ================= TERA UNIVERSAL COLOR BUTTON LOGIC =================
def get_color_inline_button(text, url, color="blue", premium_emoji_id=None):
    kwargs = {}
    api_kwargs = {}
    color_map = {"blue": "primary", "green": "success", "red": "danger", "grey": "secondary"}
    
    api_style = color_map.get(color.lower())
    if api_style:
        api_kwargs["style"] = api_style
        
    if premium_emoji_id:
        api_kwargs["icon_custom_emoji_id"] = premium_emoji_id
        
    if api_kwargs:
        kwargs["api_kwargs"] = api_kwargs
        
    return InlineKeyboardButton(text, url=url, **kwargs)

def get_exclusive_inline_keyboard():
    # Final message ke liye SIRF 1 Button blue colour aur emoji ke sath
    emoji_id = "5251717625355974982"
    link = "https://t.me/+1YoVstAHhgBjZmZl"
    
    keyboard = [
        [get_color_inline_button("All Exclusive Content", url=link, color="blue", premium_emoji_id=emoji_id)]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================= ADMIN COMMANDS =================
async def setstart_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: 
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Pehle kisi message/media par reply karke `/setstart` likho!")
        return
        
    reply = update.message.reply_to_message
    msg_data = {}
    if reply.photo: 
        msg_data = {"type": "photo", "file_id": reply.photo[-1].file_id, "text": reply.caption}
    elif reply.video: 
        msg_data = {"type": "video", "file_id": reply.video.file_id, "text": reply.caption}
    elif reply.text: 
        msg_data = {"type": "text", "file_id": None, "text": reply.text}
    else:
        await update.message.reply_text("⚠️ Sirf Text, Photo ya Video allow hai.")
        return
        
    set_msg("start", msg_data)
    await update.message.reply_text("✅ Start Message MongoDB me set ho gaya!")

async def setcontent_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: 
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Pehle kisi message/media par reply karke `/setcontent` likho!")
        return
        
    reply = update.message.reply_to_message
    msg_data = {}
    if reply.photo: 
        msg_data = {"type": "photo", "file_id": reply.photo[-1].file_id, "text": reply.caption}
    elif reply.video: 
        msg_data = {"type": "video", "file_id": reply.video.file_id, "text": reply.caption}
    elif reply.text: 
        msg_data = {"type": "text", "file_id": None, "text": reply.text}
    else:
        await update.message.reply_text("⚠️ Sirf Text, Photo ya Video allow hai.")
        return
        
    set_msg("content", msg_data)
    await update.message.reply_text("✅ Last Wala (Exclusive Content) Message MongoDB me set ho gaya!")

async def setcode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: 
        return
    
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/code <apna_code>` (e.g., `/code 646hggbb`)")
        return
        
    new_code = context.args[0]
    set_setting("access_code", new_code)
    await update.message.reply_text(f"✅ Code MongoDB me set ho gaya: `{new_code}`\n\nAb user ye code dalega tabhi use video milengi.")

async def clearmedia_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: 
        return
    
    saved_media_collection.delete_many({})
    await update.message.reply_text("🗑️ Saari purani videos Database se delete kar di gayi hain! Ab aap nayi videos bhej kar save kar sakte hain.")

# ================= DIRECT VIDEO SAVE (ADMIN ONLY) =================
async def save_admin_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
        
    if update.message.video:
        file_id = update.message.video.file_id
        media_type = "video"
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        media_type = "photo"
    else:
        return
        
    caption = update.message.caption or ""
    
    saved_media_collection.insert_one({
        "type": media_type,
        "file_id": file_id,
        "caption": caption
    })
    
    await update.message.reply_text(f"✅ {media_type.capitalize()} DB me automatically save ho gaya! (Users ko code dalne par ye milega)")

# ================= START COMMAND =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    msg = get_msg("start")
    
    if not msg or "type" not in msg:
        if user_id == OWNER_ID:
            await update.message.reply_text("⚠️ Admin: `/setstart` se message set karein.")
        else:
            await update.message.reply_text("Bot abhi start nahi hua hai, Admin ka wait karein.")
        return
        
    chat_id = update.effective_chat.id
    try:
        if msg["type"] == "photo" and msg["file_id"]: 
            await context.bot.send_photo(chat_id=chat_id, photo=msg["file_id"], caption=msg.get("text", ""))
        elif msg["type"] == "video" and msg["file_id"]: 
            await context.bot.send_video(chat_id=chat_id, video=msg["file_id"], caption=msg.get("text", ""))
        elif msg["type"] == "text" and msg.get("text"): 
            await context.bot.send_message(chat_id=chat_id, text=msg["text"])
    except Exception as e:
        print(f"Error sending start msg: {e}")

# ================= USER CODE HANDLER =================
async def handle_user_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    user_id = update.effective_user.id
    
    if not text:
        return
        
    stored_code = get_setting("access_code")
    
    if stored_code and text.strip() == stored_code:
        
        saved_media = list(saved_media_collection.find())
        
        if not saved_media:
            if user_id == OWNER_ID:
                await update.message.reply_text("⚠️ DB me koi video nahi hai. Pehle bot me direct video send karke save karein!")
            else:
                await update.message.reply_text("⚠️ Abhi koi content available nahi hai, baad me try karein.")
            return
            
        await update.message.reply_text("✅ Code matched! Aapko content bheja ja raha hai, kripya thoda wait karein...")
        
        # Ek-ek karke sari videos user ko send karna
        for item in saved_media:
            try:
                if item["type"] == "video":
                    await context.bot.send_video(chat_id=update.effective_chat.id, video=item["file_id"], caption=item.get("caption", ""))
                elif item["type"] == "photo":
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=item["file_id"], caption=item.get("caption", ""))
                
                await asyncio.sleep(0.5)  
            except Exception as e:
                print(f"Error sending media to user: {e}")
                
        # ================= AAKHIRI MESSAGE + BUTTON =================
        final_markup = get_exclusive_inline_keyboard()
        content_msg = get_msg("content")
        
        if content_msg and "type" in content_msg:
            # Agar admin ne /setcontent se message set kiya hai, toh wo bhejenge
            try:
                if content_msg["type"] == "photo" and content_msg["file_id"]: 
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=content_msg["file_id"], caption=content_msg.get("text", ""), reply_markup=final_markup)
                elif content_msg["type"] == "video" and content_msg["file_id"]: 
                    await context.bot.send_video(chat_id=update.effective_chat.id, video=content_msg["file_id"], caption=content_msg.get("text", ""), reply_markup=final_markup)
                elif content_msg["type"] == "text" and content_msg.get("text"): 
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=content_msg["text"], reply_markup=final_markup)
            except Exception as e:
                print(f"Error sending final content msg: {e}")
        else:
            # Agar admin ne koi message set nahi kiya, toh default text jayega
            await update.message.reply_text("All Exclusive Content", reply_markup=final_markup)

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Admin Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setstart", setstart_cmd))
    app.add_handler(CommandHandler("setcontent", setcontent_cmd))
    app.add_handler(CommandHandler("code", setcode_cmd))
    app.add_handler(CommandHandler("clearmedia", clearmedia_cmd))
    
    # Direct Media Save
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, save_admin_media))
    
    # Users Code Handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_text))

    print("Bot Start Ho Gaya Hai with MongoDB! Ready...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
