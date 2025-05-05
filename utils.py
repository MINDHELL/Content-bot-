import pytz, random, string  
from datetime import date 
from info import API, URL
from shortzy import Shortzy

TOKENS = {}
VERIFIED = {}

async def get_verify_shorted_link(link):
    shortzy = Shortzy(api_key=API, base_site=URL)
    link = await shortzy.convert(link)
    return link

async def check_token(bot, userid, token):
    user = await bot.get_users(userid)
    if user.id in TOKENS:
        # Check if the user has any tokens and if the token exists for that user
        user_tokens = TOKENS[user.id]
        if token in user_tokens:
            is_used = user_tokens[token]
            if is_used:
                return False  # Token has been used already
            else:
                return True  # Token is valid (unused)
    return False  # No token found for the user

async def get_token(bot, userid, link):
    user = await bot.get_users(userid)
    # Generate a new unique token
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=7))
    if user.id not in TOKENS:
        TOKENS[user.id] = {}
    TOKENS[user.id][token] = False  # Add the token to the user's token dictionary with False (not used)
    link = f"{link}verify-{user.id}-{token}"
    shortened_verify_url = await get_verify_shorted_link(link)
    return str(shortened_verify_url)

async def verify_user(bot, userid, token):
    user = await bot.get_users(userid)
    # Update the token to True (used)
    if user.id in TOKENS and token in TOKENS[user.id]:
        TOKENS[user.id][token] = True
        # Record verification date
        tz = pytz.timezone('Asia/Kolkata')
        today = date.today()
        VERIFIED[user.id] = str(today)  # Store the verification date

async def check_verification(bot, userid):
    user = await bot.get_users(userid)
    today = date.today()
    if user.id in VERIFIED:
        exp_date = VERIFIED[user.id]
        exp_year, exp_month, exp_day = map(int, exp_date.split('-'))
        expiry = date(exp_year, exp_month, exp_day)
        if expiry < today:
            return False  # Verification has expired
        return True  # Still valid
    return False  # No verification record found
