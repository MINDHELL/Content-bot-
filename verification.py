import pytz, random, string
from datetime import date
from info import API, URL
from shortzy import Shortzy

TOKENS = {}
VERIFIED = {}

async def get_verify_shorted_link(link):
    shortzy = Shortzy(api_key=API, base_site=URL)
    return await shortzy.convert(link)

async def get_token(bot, userid, link):
    user = await bot.get_users(userid)
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=7))
    
    # Keep old tokens and add new
    if user.id not in TOKENS:
        TOKENS[user.id] = {}
    TOKENS[user.id][token] = False

    full_link = f"{link}verify-{user.id}-{token}"
    return await get_verify_shorted_link(full_link)

async def check_token(bot, userid, token):
    user = await bot.get_users(userid)
    user_tokens = TOKENS.get(user.id, {})
    return token in user_tokens and not user_tokens[token]

async def verify_user(bot, userid, token):
    user = await bot.get_users(userid)
    if user.id in TOKENS and token in TOKENS[user.id]:
        TOKENS[user.id][token] = True  # Mark as used
    VERIFIED[user.id] = date.today().isoformat()  # 'YYYY-MM-DD'

async def check_verification(bot, userid):
    user = await bot.get_users(userid)
    if user.id in VERIFIED:
        try:
            verified_date = date.fromisoformat(VERIFIED[user.id])
            return verified_date >= date.today()  # Valid for today only
        except ValueError:
            return False
    return False
