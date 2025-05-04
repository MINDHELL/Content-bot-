import random, string
from datetime import date
import pytz
from info import API, URL
from shortzy import Shortzy

# Memory storage (can later be moved to database)
TOKENS = {}
VERIFIED = {}

BONUS_QUOTA = 30  # Number of videos granted on verification

async def get_verify_shorted_link(link):
    shortzy = Shortzy(api_key=API, base_site=URL)
    return await shortzy.convert(link)

async def generate_token(userid):
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=7))
    TOKENS[userid] = {token: False}
    return token

async def get_token_link(client, userid, link):
    token = await generate_token(userid)
    full_link = f"{link}verify-{userid}-{token}"
    return await get_verify_shorted_link(full_link)

async def check_token(userid, token):
    if userid in TOKENS and token in TOKENS[userid] and TOKENS[userid][token] is False:
        return True
    return False

async def verify_user(userid, token):
    if userid in TOKENS and token in TOKENS[userid]:
        TOKENS[userid][token] = True
        VERIFIED[userid] = str(date.today())
        return True
    return False

async def is_verified(userid):
    today = str(date.today())
    return VERIFIED.get(userid) == today
