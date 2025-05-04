import os
import logging
import asyncio
import threading
import time
import re
import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BotCommand
from pymongo import MongoClient
from pyrogram.errors import InputUserDeactivated, UserNotParticipant, FloodWait, UserIsBlocked, PeerIdInvalid
from health_check import start_health_check
from pyrogram import Client, filters
from verification import check_verification, get_token, check_token, verify_user
from info import VERIFY, BOT_USERNAME, VERIFY_TUTORIAL

# 🔰 Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔰 Environment Variables
API_ID = int(os.getenv("API_ID", "27788368"))
API_HASH = os.getenv("API_HASH", "9df7e9ef3d7e4145270045e5e43e1081")
BOT_TOKEN = os.getenv("BOT_TOKEN", "7692429836:AAFhPqKJghT0G524pxCobrj-XfiXefTGnmA")
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://aarshhub:6L1PAPikOnAIHIRA@cluster0.6shiu.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1002465297334"))
OWNER_ID = int(os.getenv("OWNER_ID", "6860316927"))
WELCOME_IMAGE = os.getenv("WELCOME_IMAGE", "https://envs.sh/n9o.jpg")
AUTO_DELETE_TIME = int(os.getenv("AUTO_DELETE_TIME", "7200"))
VIDEO_LIMIT = int(os.getenv("VIDEO_LIMIT", "15"))  # Set video limit per user
DEFAULT_QUOTA_RESET_TIME = int(os.getenv("DEFAULT_QUOTA_RESET_TIME", "86400"))  # Default quota reset time in seconds (24 hours)

# ✅ Force Subscribe Setup
id_pattern = re.compile(r'^.\d+$')
AUTH_CHANNEL = [int(ch) if id_pattern.search(ch) else ch for ch in os.getenv("AUTH_CHANNEL", "-1002490575006").split()]

# 🔰 Initialize Bot & Database
bot = Client("video_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
mongo = MongoClient(MONGO_URL)
db = mongo["VideoBot1"]
collection = db["videos1"]
users_collection = db["users1"]
settings_collection = db["settings1"]

# ✅ **Cache Optimization**
video_cache = []
last_cache_time = 0
CACHE_EXPIRY = 300  # Refresh cache every 5 minutes

async def refresh_video_cache():
    global video_cache, last_cache_time
    if time.time() - last_cache_time > CACHE_EXPIRY:
        video_cache = list(collection.aggregate([{"$sample": {"size": 500}}]))  
        last_cache_time = time.time()

# ✅ **Fetch Protection Setting**
def is_protection_enabled():
    setting = settings_collection.find_one({"_id": "content_protection"})
    return setting and setting.get("enabled", True)

# ✅ **User Management**
async def add_user(user_id):
    user = users_collection.find_one({"id": user_id})
    if not user:
        # Initialize user with default values
        users_collection.insert_one({
            "id": user_id,
            "joined": datetime.datetime.utcnow(),
            "videos_sent": 0,  # Initialize videos_sent field
            "quota_reset_time": time.time() + DEFAULT_QUOTA_RESET_TIME  # Set the reset time for quota
        })
    else:
        # Ensure "videos_sent" and "quota_reset_time" exist
        if "videos_sent" not in user:
            users_collection.update_one({"id": user_id}, {"$set": {"videos_sent": 0}})
        if "quota_reset_time" not in user:
            users_collection.update_one({"id": user_id}, {"$set": {"quota_reset_time": time.time() + DEFAULT_QUOTA_RESET_TIME}})

# ✅ **/users Command – Get Total Users**
@bot.on_message(filters.command("users") & filters.user(OWNER_ID))
async def get_users_count(client, message):
    total_users = users_collection.count_documents({})
    await message.reply_text(f"📊 **Total Users:** `{total_users}`")

# ✅ **Broadcast System**
async def broadcast_messages(user_id, message):
    try:
        await message.copy(chat_id=user_id)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await broadcast_messages(user_id, message)
    except (InputUserDeactivated, UserIsBlocked, PeerIdInvalid):
        users_collection.delete_one({"id": user_id})
        return False, "Removed"
    except Exception:
        return False, "Error"

@bot.on_message(filters.command("broadcast") & filters.user(OWNER_ID) & filters.reply)
async def broadcast(client, message):
    users = users_collection.find()
    b_msg = message.reply_to_message
    total_users = users_collection.count_documents({})
    done, blocked, deleted, failed, success = 0, 0, 0, 0, 0

    status_msg = await message.reply_text(f"📢 **Broadcasting...**\nTotal Users: `{total_users}`")
    start_time = time.time()

    for user in users:
        user_id = user.get("id")
        if not user_id:
            continue
            
        result, reason = await broadcast_messages(user_id, b_msg)
        if result:
            success += 1
        else:
            if reason == "Removed":
                deleted += 1
            failed += 1
        done += 1

        if done % 20 == 0:
            try:
                await status_msg.edit(f"📢 **Broadcasting...**\nTotal Users: `{total_users}`\nProcessed: `{done}`\n✅ Success: `{success}`\n❌ Failed: `{failed}`\n🚫 Deleted: `{deleted}`")
            except:
                pass

    time_taken = datetime.timedelta(seconds=int(time.time() - start_time))
    await status_msg.edit(f"✅ **Broadcast Completed in {time_taken}!**\nTotal Users: `{total_users}`\nProcessed: `{done}`\n✅ Success: `{success}`\n❌ Failed: `{failed}`\n🚫 Deleted: `{deleted}`")

# ✅ **Start Command**
@bot.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    await add_user(user_id)

    if AUTH_CHANNEL:
        try:
            btn = []
            for id in AUTH_CHANNEL:
                chat = await client.get_chat(int(id))
                await client.get_chat_member(id, user_id)
        except UserNotParticipant:
            btn.append([InlineKeyboardButton(f'Join {chat.title}', url=chat.invite_link)])
            btn.append([InlineKeyboardButton("♻️ Try Again ♻️", url=f"https://t.me/{client.me.username}?start=true")])
            await message.reply_text(
                f"👋 **Hello {message.from_user.mention},**\n\nJoin the channel and click 'Try Again'.",
                reply_markup=InlineKeyboardMarkup(btn),
            )
            return
        except Exception:
            pass

    # Check if user is verified
    if not await check_verification(client, user_id):
        # If not verified, send verification instructions
        verification_url = await get_token(client, user_id, "https://telegram.me/{BOT_USERNAME}?start=")
        
        btn = [
            [InlineKeyboardButton("Verify", url=verification_url)],
            [InlineKeyboardButton("How To Open Link & Verify", url=VERIFY_TUTORIAL)]
        ]
        
        await message.reply_text(
            text="<b>You are not verified! Kindly verify to continue.</b>",
            reply_markup=InlineKeyboardMarkup(btn),
            protect_content=True
        )
        return

    # If verified, proceed with bot's main functionality
    await message.reply_text("Welcome! You are verified and can use the bot.")

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎥 Get Random Video", callback_data="get_random_video")]])
    await message.reply_photo(WELCOME_IMAGE, caption="🎉 Welcome to the Video Bot!\n\n<b>𝖳𝗁𝗂𝗌 𝖡𝗈𝗍 𝖢𝗈𝗇𝗍𝖺𝗂𝗇𝗌 18+ 𝖢𝗈𝗇𝗍𝖾𝗇𝗍 𝖲𝗈 𝖪𝗂𝗇𝖽𝗅𝗒 𝖠𝖼𝖼𝖾𝗌𝗌 𝖨𝗍 𝖶𝗂𝗍𝗁 𝖸𝗈𝗎𝗋 𝖮𝗐𝗇 𝖱𝗂𝗌𝗄. 𝖳𝗁𝖾 𝖬𝖺𝗍𝖾𝗋𝗂𝖺𝗅 𝖬𝖺𝗒 𝖨𝗇𝖼𝗅𝗎𝖽𝖾 𝖤𝗑𝗉𝗅𝗂𝖼𝗂𝗍 𝖮𝗋 𝖦𝗋𝖺𝗉𝗁𝗂𝖼 𝖢𝗈𝗇𝗍𝖺𝖼𝗍 𝖳𝗁𝖺𝗍 𝖨𝗌 𝖴𝗇𝗌𝗎𝗂𝗍𝖺𝖻𝗅𝖾 𝖥𝗈𝗋 𝖬𝗂𝗇𝗈𝗋𝗌. 𝖲𝗈 𝖢𝗁𝗂𝗅𝖽𝗋𝖾𝗇𝗌 𝖯𝗅𝖾𝖺𝗌𝖾 𝖲𝗍𝖺𝗒 𝖠𝗐𝖺𝗒.</b>\n\n 𝖯𝗅𝖾𝖺𝗌𝖾 𝖢𝗁𝖾𝖼𝗄 Disclaimer and About 𝖡𝖾𝖿𝗈𝗋𝖾 𝖴𝗌𝗂𝗇𝗀 𝖳𝗁𝗂𝗌 𝖡𝗈𝗍..\n\n ", reply_markup=keyboard)


# ✅ **Get Random Video**
async def send_random_video(client, chat_id):
    await refresh_video_cache()

    if not video_cache:
        await client.send_message(chat_id, "⚠ No videos available. Use /index first!")
        return

    # Check if user is the owner (unlimited quota)
    if chat_id == OWNER_ID:
        user = {"videos_sent": 0, "quota_reset_time": time.time()}
    else:
        user = users_collection.find_one({"id": chat_id})

    if user["videos_sent"] >= VIDEO_LIMIT and time.time() < user["quota_reset_time"]:
        reset_time = datetime.datetime.fromtimestamp(user["quota_reset_time"]).strftime("%Y-%m-%d %H:%M:%S")
        await client.send_message(
            chat_id,
            f"⚠️ You have reached your video limit of {VIDEO_LIMIT} videos. Your quota will reset at {reset_time}.",
        )
        return

    video = video_cache.pop()
    try:
        message = await client.get_messages(CHANNEL_ID, video["message_id"])
        if message and message.video:
            sent_msg = await client.send_video(
                chat_id, video=message.video.file_id, caption="Thanks 😊", protect_content=True
            )

            if chat_id != OWNER_ID:  # Only update quota for non-owner users
                users_collection.update_one({"id": chat_id}, {"$inc": {"videos_sent": 1}})

            if AUTO_DELETE_TIME > 0:
                await asyncio.sleep(AUTO_DELETE_TIME)
                await sent_msg.delete()

    except FloodWait as e:
        await asyncio.sleep(e.value)
        await send_random_video(client, chat_id)

@Client.on_message(filters.regex("verify"))
async def verify(client, message):
    # Extract user ID and token from the message
    data = message.command[1]
    userid = data.split("-", 2)[1]
    token = data.split("-", 3)[2]

    if str(message.from_user.id) != str(userid):
        return await message.reply_text(
            text="<b>Invalid link or expired link!</b>",
            protect_content=True
        )

    # Check token validity
    is_valid = await check_token(client, userid, token)
    if is_valid:
        await verify_user(client, userid, token)
        await message.reply_text(
            text=f"<b>Hey {message.from_user.mention}, You are successfully verified!</b>",
            protect_content=True
        )
    else:
        return await message.reply_text(
            text="<b>Invalid link or expired link!</b>",
            protect_content=True
        )


@bot.on_callback_query(filters.regex("get_random_video"))
async def random_video_callback(client, callback_query: CallbackQuery):
    await callback_query.answer()
    asyncio.create_task(send_random_video(client, callback_query.message.chat.id))


# ✅ **Quota Status**
@bot.on_message(filters.command("quota"))
async def quota_status(client, message):
    user_id = message.from_user.id
    if user_id == OWNER_ID:
        await message.reply_text("✅ **You are the owner and have unlimited quota!**")
        return

    user = users_collection.find_one({"id": user_id})
    if user:
        videos_left = max(0, VIDEO_LIMIT - user["videos_sent"])
        current_time = time.time()
        
        # If the quota reset time has already passed, reset it
        if current_time > user["quota_reset_time"]:
            new_reset_time = current_time + settings_collection.find_one({"_id": "quota_settings"})["quota_reset_time"]
            users_collection.update_one({"id": user_id}, {"$set": {"quota_reset_time": new_reset_time, "videos_sent": 0}})
        else:
            new_reset_time = user["quota_reset_time"]
            
            reset_time = datetime.datetime.fromtimestamp(new_reset_time).strftime("%Y-%m-%d %H:%M:%S")
            time_left = max(0, new_reset_time - current_time)
            
            await message.reply_text(
            f"📊 **Your Quota Status:**\n"
            f"📅 Quota Reset Time: {reset_time}\n"
            f"🎥 Videos Sent: {user['videos_sent']}/{VIDEO_LIMIT}\n"
            f"⏳ Time Until Reset: {str(datetime.timedelta(seconds=int(time_left)))}\n"
            f"🕒 Videos Left: {videos_left}"
        )
    else:
        await message.reply_text("⚠️ User not found! Please start the bot first.")


# ✅ **Set Quota Duration (Only for Owner)**
@bot.on_message(filters.command("setquota") & filters.user(OWNER_ID))
async def set_quota_duration(client, message):
    try:
        _, hours = message.text.split()
        hours = int(hours)
        new_quota_reset_time = hours * 60 * 60  # Convert hours to seconds

        settings_collection.update_one(
            {"_id": "quota_settings"}, {"$set": {"quota_reset_time": new_quota_reset_time}}, upsert=True
        )
        
        # Update all users' quota reset time immediately
        current_time = time.time()
        users_collection.update_many(
            {}, {"$set": {"quota_reset_time": current_time + new_quota_reset_time}}
        )

        await message.reply_text(f"✅ **Quota reset duration updated to {hours} hours!**")
    except (ValueError, IndexError):
        await message.reply_text("⚠ Usage: `/setquota <hours>` (e.g., `/setquota 6` for 6 hours)")


@bot.on_message(filters.command("getquota") & filters.user(OWNER_ID))
async def get_quota_setting(client, message):
    settings = settings_collection.find_one({"_id": "quota_settings"})
    if settings and "quota_reset_time" in settings:
        duration = str(datetime.timedelta(seconds=settings["quota_reset_time"]))
        await message.reply_text(f"⏱ **Current quota reset duration:** `{duration}`")
    else:
        await message.reply_text("⚠ No custom quota reset duration set.")
        

# ✅ **Index Videos**
@bot.on_message(filters.command("index") & filters.user(OWNER_ID))
async def index_videos(client, message):
    await message.reply_text("🔄 Indexing videos...")

    last_indexed = collection.find_one(sort=[("message_id", -1)])
    last_message_id = last_indexed["message_id"] if last_indexed else 1
    indexed_count = 0

    while True:
        try:
            messages = await client.get_messages(CHANNEL_ID, list(range(last_message_id, last_message_id + 100)))
            video_entries = [
                {"message_id": msg.id} for msg in messages if msg and msg.video and not collection.find_one({"message_id": msg.id})
            ]

            if video_entries:
                collection.insert_many(video_entries)
                indexed_count += len(video_entries)

            last_message_id += 100
            if not video_entries:
                break
        except Exception:
            break

    await refresh_video_cache()
    await message.reply_text(f"✅ Indexed {indexed_count} new videos!" if indexed_count else "⚠ No new videos found!")


@bot.on_message(filters.command("files") & filters.user(OWNER_ID))
async def total_files(client, message):
    total_files = collection.count_documents({})
    await message.reply_text(f"📂 **Total Indexed Files:** `{total_files}`")


@bot.on_message(filters.command("disclaimer"))
async def disclaimer_message(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Close", callback_data="close_disclaimer")]
    ])
    await message.reply_text(
        "**Disclaimer & Terms of Service**\n\n"
        "1. This bot is intended for educational and entertainment purposes only.\n"
        "2. We do not host or promote any copyrighted content.\n"
        "3. All media is shared from publicly available sources.\n"
        "4. Users are responsible for the content they access.\n"
        "5. We reserve the right to block users for misuse or abuse.\n"
        "6. FOR ANY ISSUE DM OWNER @XSUPPRT3BOT.\n\n" 
        "By using this bot, you agree to these terms.",
        reply_markup=keyboard
    )
    

@bot.on_callback_query(filters.regex("close_disclaimer"))
async def close_disclaimer_callback(client, callback_query: CallbackQuery):
    await callback_query.message.delete()


@bot.on_message(filters.command("about"))
async def about_command(client, message):
    await message.reply_text(
        text=(
            f"<b>○ Creator : <a href='https://t.me/Xsupprt3bot'>This Person</a>\n"
            f"○ Language : <code>Python3</code>\n"
            f"○ Library : <a href='https://docs.pyrogram.org/'>Pyrogram asyncio</a>\n"
            f"○ Source Code : <a href='https://t.me/Xsupprt3bot'>Click here </a>\n"
            f"○ Channel : @Allvidsbackup3\n"
            f"○ Support Group : @Xsupport_chats</b>"
        ),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔒 Close", callback_data="close")]
        ])
    )

@bot.on_callback_query()
async def handle_close_button(client, query: CallbackQuery):
    if query.data == "close":
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass



# ✅ **Run the Bot**
if __name__ == "__main__":
    threading.Thread(target=start_health_check, daemon=True).start()
    bot.run()
