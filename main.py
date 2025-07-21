import asyncio
import datetime
import re
import os
from telethon import TelegramClient, events, Button
from telethon.errors.rpcerrorlist import (
    FloodWaitError, SessionPasswordNeededError, PhoneNumberInvalidError,
    PhoneCodeInvalidError, PasswordHashInvalidError
)
from telethon.sessions import StringSession

# ########################################
# ### بخش تنظیمات اصلی ربات            ###
# ########################################

# --- این مقادیر باید توسط شما پر شوند ---
# توکن رباتی که از @BotFather گرفته‌اید
BOT_TOKEN = '7868759557:AAFnM3IZNfgogWw0HyINjO3Q9f9Q4nBjuAs'
# API ID و API HASH حسابی که ربات با آن کار می‌کند (می‌تواند حساب شخصی شما باشد)
BOT_API_ID = 9309709  # <-- API ID خود را وارد کنید
BOT_API_HASH = 'cba32691d5804bc435725c6ce0a3c27c' # <-- API HASH خود را وارد کنید

# کانال های مبدا و مقصد
SOURCE_CHANNEL_ID = '@MTP_roto'
DESTINATION_CHANNEL_ID = '@proxy1321'

# زمانبندی ارسال پیام ها
SCHEDULED_TIMES = ["09:30", "10:30", "11:30", "12:30", "13:30", "14:30",
                   "15:30", "16:30", "17:30", "18:30", "19:30", "20:30",
                   "21:30", "22:30", "23:30"]

# برای نگهداری کلاینت‌های فعال کاربران
# ساختار: {chat_id: {'client': user_client, 'task': scheduler_task}}
ACTIVE_CLIENTS = {}
lock = asyncio.Lock()

# ########################################
# ### توابع اصلی برنامه                  ###
# ########################################

def decrypt_code(encrypted_code):
    """
    هر رقم از کد رمزنگاری شده را یکی کم می‌کند.
    مثال: رشته '810' به '709' تبدیل می‌شود.
    """
    if not encrypted_code.isdigit():
        return encrypted_code # اگر ورودی عدد نبود، همان را برگردان
        
    decrypted = ''
    for digit in encrypted_code:
        # (int(digit) - 1 + 10) % 10 برای مدیریت صحیح عدد 0 است
        # (0 - 1 + 10) % 10 = 9
        original_digit = (int(digit) - 1 + 10) % 10
        decrypted += str(original_digit)
    return decrypted


def format_proxy_message(text):
    """فرمت کردن پیام پراکسی برای ارسال در کانال مقصد."""
    lines = text.splitlines()

    location_line = next((line.replace("**", "").strip() for line in lines if 'Location' in line), '')
    secret_line = next((line for line in lines if 'Secret:' in line), '')

    url_match = re.search(r'(https?://\S+)', secret_line)
    secret_url = url_match.group(1) if url_match else ''
    if secret_url.endswith(')'):
        secret_url = secret_url[:-1]

    formatted_text = (
        "AzadVPNPro | Proxy پروکسی 🔒\n\n"
        f"{location_line}\n"
        "Speed: Ultra Fast⚡️ \n\n"
        f"Connect here:\n\n{secret_url}\n\n\n\n\n"
        "Channel: @AzadvpnPro\n"
        "Support: @Aliwjafari"
    )
    return formatted_text, secret_url


async def copy_and_send_last_message(client):
    """
    آخرین پیام را کپی و ارسال می‌کند.
    در صورت موفقیت یا شکست، یک پیام متنی برای گزارش برمی‌گرداند.
    """
    async with lock:
        try:
            source_entity = await client.get_entity(SOURCE_CHANNEL_ID)
            destination_entity = await client.get_entity(DESTINATION_CHANNEL_ID)

            messages = await client.get_messages(source_entity, limit=1)
            if not messages or not messages[0].text:
                return "ℹ️ پیام جدیدی برای ارسال یافت نشد یا آخرین پیام متنی نبود."

            last_message = messages[0]
            formatted_text, secret_url = format_proxy_message(last_message.text)
            
            await client.send_message(
                destination_entity,
                formatted_text,
                buttons=[Button.url('Connect here', secret_url)],
                link_preview=False,
                parse_mode='md'
            )
            return f"✅ پیام با شناسه {last_message.id} با موفقیت ارسال شد."

        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
            return f"⏳ به دلیل محدودیت تلگرام، عملیات برای {e.seconds} ثانیه متوقف شد."
        except Exception as e:
            print(f"Error in copy_and_send_last_message: {e}")
            return f"❌ خطایی در ارسال پیام رخ داد: {e}"


async def scheduler(user_client, bot_client, chat_id):
    """وظیفه زمانبندی را اجرا کرده و به کاربر گزارش می‌دهد."""
    print(f"Scheduler started for chat_id: {chat_id}")
    while True:
        try:
            now = datetime.datetime.now().strftime("%H:%M")
            if now in SCHEDULED_TIMES:
                await bot_client.send_message(chat_id, "ℹ️ زمان ارسال فرا رسید، در حال اجرای عملیات زمان‌بندی شده...")
                report = await copy_and_send_last_message(user_client)
                await bot_client.send_message(chat_id, f"📃 **نتیجه عملیات زمان‌بندی:**\n{report}")
                await asyncio.sleep(61)  # جلوگیری از اجرای دوباره در همان دقیقه
            
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            print(f"Scheduler cancelled for chat_id: {chat_id}")
            break
        except Exception as e:
            print(f"Error in scheduler for {chat_id}: {e}")
            await bot_client.send_message(chat_id, f"❌ خطای جدی در زمان‌بندی رخ داد: {e}")
            await asyncio.sleep(60)


# ########################################
# ### بخش مدیریت ربات و تعامل با کاربر ###
# ########################################

bot = TelegramClient('bot_session', BOT_API_ID, BOT_API_HASH)

def get_main_menu(chat_id):
    """منوی اصلی را بر اساس وضعیت ورود کاربر برمی‌گرداند."""
    if chat_id in ACTIVE_CLIENTS:
        buttons = [
            [Button.text("⚡️ اجرای دستی عملیات")],
            [Button.text("🚪 خروج از حساب")]
        ]
        text = "شما با موفقیت وارد شده‌اید. چه کاری می‌خواهید انجام دهید؟"
    else:
        buttons = [Button.text("🚀 شروع فرآیند ورود", resize=True)]
        text = "سلام! 👋\nبرای شروع فرآیند کپی خودکار پیام‌ها، روی دکمه زیر کلیک کنید."
    return text, buttons


@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """پاسخ به دستور /start و نمایش منوی مناسب."""
    chat_id = event.chat_id
    text, buttons = get_main_menu(chat_id)
    await event.respond(text, buttons=buttons)


@bot.on(events.NewMessage(pattern='🚀 شروع فرآیند ورود'))
async def login_handler(event):
    """مدیریت فرآیند کامل ورود به حساب کاربری با رفع مشکل انتظار و افزودن رمزگشایی."""
    chat_id = event.chat_id
    if chat_id in ACTIVE_CLIENTS:
        text, buttons = get_main_menu(chat_id)
        await event.respond("شما از قبل وارد شده‌اید.", buttons=buttons)
        return

    user_client = None
    try:
        async with bot.conversation(chat_id, timeout=300) as conv:
            await conv.send_message("1️⃣ لطفا `API_ID` حساب کاربری خود را وارد کنید.\n\nبرای لغو /cancel را بنویسید.")
            api_id_resp = await conv.get_response()
            if api_id_resp.text == '/cancel': return await conv.send_message("فرآیند لغو شد.")
            api_id = api_id_resp.text

            await conv.send_message("2️⃣ عالی! حالا `API_HASH` را وارد کنید.")
            api_hash_resp = await conv.get_response()
            if api_hash_resp.text == '/cancel': return await conv.send_message("فرآیند لغو شد.")
            api_hash = api_hash_resp.text
            
            await conv.send_message("3️⃣ بسیار خب. شماره تلفن خود را با فرمت بین‌المللی وارد کنید.\nمثال: `+989123456789`")
            phone_resp = await conv.get_response()
            if phone_resp.text == '/cancel': return await conv.send_message("فرآیند لغو شد.")
            phone = phone_resp.text

            await conv.send_message("⏳ در حال تلاش برای اتصال...")
            
            user_client = TelegramClient(StringSession(), int(api_id), api_hash)
            await user_client.connect()

            try:
                code_request = await user_client.send_code_request(phone)
                
                # ######################################################
                # ### شروع بخش اصلاح شده برای دریافت کد ورود ###
                # ######################################################
                await conv.send_message(
                    "4️⃣ یک کد به تلگرام شما ارسال شد. لطفاً آن را به صورت رمزنگاری شده (هر رقم + یک) وارد کنید.\nمثال: اگر کد `12345` است شما `23456` را ارسال کنید."
                )
                user_code_resp = await conv.get_response()
                if user_code_resp.text == '/cancel': return await conv.send_message("فرآیند لغو شد.")
                
                # رمزگشایی کد دریافت شده از کاربر
                decrypted_code = decrypt_code(user_code_resp.text)
                
                await user_client.sign_in(phone, decrypted_code, phone_code_hash=code_request.phone_code_hash)
                # ######################################################
                # ### پایان بخش اصلاح شده ###
                # ######################################################

            except SessionPasswordNeededError:
                # ######################################################
                # ### شروع بخش اصلاح شده برای دریافت رمز عبور ###
                # ######################################################
                await conv.send_message(
                    "5️⃣ حساب شما رمز تایید دو مرحله‌ای دارد. لطفاً رمز را وارد کنید."
                )
                password_resp = await conv.get_response()
                if password_resp.text == '/cancel': return await conv.send_message("فرآیند لغو شد.")
                
                await user_client.sign_in(password=password_resp.text)
                # ######################################################
                # ### پایان بخش اصلاح شده ###
                # ######################################################

            me = await user_client.get_me()
            await conv.send_message(f"✅ ورود موفقیت آمیز بود! خوش آمدید {me.first_name}.")
            
            task = asyncio.create_task(scheduler(user_client, bot, chat_id))
            ACTIVE_CLIENTS[chat_id] = {'client': user_client, 'task': task}
            
            text, buttons = get_main_menu(chat_id)
            await conv.send_message(text, buttons=buttons)

    except (PhoneCodeInvalidError, PasswordHashInvalidError):
        await event.respond("❌ کد یا رمز عبور اشتباه است. لطفاً دوباره با /start تلاش کنید.")
    except PhoneNumberInvalidError:
        await event.respond("❌ فرمت شماره تلفن اشتباه است. لطفاً دوباره با /start تلاش کنید.")
    except asyncio.TimeoutError:
        await event.respond("⏰ زمان پاسخگویی تمام شد. لطفاً دوباره تلاش کنید.")
    except Exception as e:
        await event.respond(f"❌ یک خطای پیش‌بینی نشده رخ داد: {e}\nلطفاً دوباره با /start تلاش کنید.")
        if user_client and user_client.is_connected():
            await user_client.disconnect()

@bot.on(events.NewMessage(pattern='⚡️ اجرای دستی عملیات'))
async def manual_run_handler(event):
    """اجرای دستی عملیات کپی و ارسال پیام."""
    chat_id = event.chat_id
    if chat_id not in ACTIVE_CLIENTS:
        await event.respond("ابتدا باید با دستور /start وارد شوید.")
        return

    await event.respond("⏳ در حال اجرای دستی عملیات...")
    user_client = ACTIVE_CLIENTS[chat_id]['client']
    report = await copy_and_send_last_message(user_client)
    await event.respond(f"📃 **نتیجه عملیات دستی:**\n{report}")


@bot.on(events.NewMessage(pattern='🚪 خروج از حساب'))
async def logout_handler(event):
    """خروج کاربر از حساب و پاک کردن نشست."""
    chat_id = event.chat_id
    if chat_id in ACTIVE_CLIENTS:
        await event.respond("⏳ در حال خروج از حساب...")
        
        # لغو تسک زمان‌بندی
        ACTIVE_CLIENTS[chat_id]['task'].cancel()
        
        # قطع اتصال کلاینت کاربر
        await ACTIVE_CLIENTS[chat_id]['client'].disconnect()
        
        # حذف از لیست کاربران فعال
        del ACTIVE_CLIENTS[chat_id]
        
        await event.respond("✅ شما با موفقیت از حساب خارج شدید.", buttons=get_main_menu(chat_id)[1])
    else:
        await event.respond("شما هنوز وارد نشده‌اید.", buttons=get_main_menu(chat_id)[1])


async def main():
    """تابع اصلی برای اجرای ربات."""
    await bot.start(bot_token=BOT_TOKEN)
    print("Bot started...")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    print("ربات در حال اجراست. برای توقف Ctrl+C را فشار دهید.")
    asyncio.run(main())
