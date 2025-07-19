#import asyncio
#import datetime
#import re
#import os
#import json
#from zoneinfo import ZoneInfo
#from telethon import TelegramClient, events, Button
#from telethon.errors.rpcerrorlist import (
    FloodWaitError, SessionPasswordNeededError, PhoneNumberInvalidError,
    PhoneCodeInvalidError, PasswordHashInvalidError
)
#from telethon.sessions import StringSession


BOT_TOKEN = '7893622007:AAEspjMopanFXqa2YGuXdOor51VUs27vzJg'
BOT_API_ID = 9309709
BOT_API_HASH = 'cba32691d5804bc435725c6ce0a3c27c'

USER_DATA_FILE = "user_data.json"

DEFAULT_SCHEDULED_TIMES = ["09:30", "10:30", "11:30", "12:30", "13:30", "14:30",
                           "15:30", "16:30", "17:30", "18:30", "19:30", "20:30",
                           "21:30", "22:30", "23:30"]

DEFAULT_MESSAGE_TEMPLATE = (
    "AzadVPNPro | Proxy پروکسی\n\n"
    "Location: [location]\n"
    "Speed: Ultra Fast\n\n"
    "Connect here:\n\n[link]\n\n\n\n\n"
    "Channel: @AzadvpnPro\n"
    "Support: @Aliwjafari"
)

ACTIVE_USER_SESSION = {}
lock = asyncio.Lock()
NEEDS_LOGIN_MESSAGE = "برای دسترسی به این بخش، ابتدا باید وارد حساب کاربری خود شوید."


def save_user_data():
    if not ACTIVE_USER_SESSION:
        return
    user_data = ACTIVE_USER_SESSION
    data_to_save = {
        'session_string': user_data['client'].session.save(),
        'schedule': user_data.get('schedule', []),
        'template': user_data.get('template', DEFAULT_MESSAGE_TEMPLATE),
        'chat_id': user_data.get('chat_id'),
        'source_channel': user_data.get('source_channel'),
        'destination_channel': user_data.get('destination_channel')
    }
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(data_to_save, f)

def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    return None

def delete_user_data():
    if os.path.exists(USER_DATA_FILE):
        os.remove(USER_DATA_FILE)

def decrypt_code(encrypted_code):
    if not encrypted_code.isdigit(): return encrypted_code
    decrypted = ''
    for digit in encrypted_code:
        original_digit = (int(digit) - 1 + 10) % 10
        decrypted += str(original_digit)
    return decrypted

def extract_proxy_details(text):
    lines = text.splitlines()
    location = next((line.replace("**", "").replace("Location:", "").strip() for line in lines if 'Location' in line), 'N/A')
    secret_line = next((line for line in lines if 'Secret:' in line), '')
    url_match = re.search(r'(https?://\S+)', secret_line)
    link = url_match.group(1) if url_match else ''
    if link.endswith(')'): link = link[:-1]
    return location, link

def format_message_with_template(template, location, link):
    return template.replace('[location]', location).replace('[link]', link)

async def copy_and_send_last_message(client, chat_id):
    async with lock:
        source_channel = ACTIVE_USER_SESSION.get('source_channel')
        destination_channel = ACTIVE_USER_SESSION.get('destination_channel')
        if not source_channel or not destination_channel:
            return "خطا: کانال‌های مبدا و مقصد تنظیم نشده‌اند. لطفا از منوی اصلی آن‌ها را تنظیم کنید."

        try:
            user_template = ACTIVE_USER_SESSION.get('template', DEFAULT_MESSAGE_TEMPLATE)
            source_entity = await client.get_entity(source_channel)
            destination_entity = await client.get_entity(destination_channel)
            messages = await client.get_messages(source_entity, limit=1)
            if not messages or not messages[0].text:
                return "پیام جدیدی برای ارسال یافت نشد."
            last_message_text = messages[0].text
            location, secret_url = extract_proxy_details(last_message_text)
            if not secret_url:
                return f"خطا: لینک پروکسی در پیام با شناسه {messages[0].id} یافت نشد."
            formatted_text = format_message_with_template(user_template, location, secret_url)
            await client.send_message(destination_entity, formatted_text, buttons=[Button.url('اتصال', secret_url)], link_preview=False, parse_mode='md')
            return f"پیام با شناسه {messages[0].id} با موفقیت به کانال مقصد ارسال شد."
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
            return f"به دلیل محدودیت تلگرام، عملیات برای {e.seconds} ثانیه متوقف شد."
        except Exception as e:
            print(f"Error in copy_and_send_last_message: {e}")
            return f"خطا در ارسال پیام: {e}"

async def scheduler(user_client, bot_client, chat_id, schedule_list):
    print(f"زمان‌بند برای کاربر با چت آی‌دی {chat_id} و {len(schedule_list)} زمان، شروع به کار کرد.")
    while True:
        try:
            now = datetime.datetime.now(ZoneInfo("Asia/Tehran")).strftime("%H:%M")
            if now in schedule_list:
                await bot_client.send_message(chat_id, "زمان ارسال فرا رسید، در حال اجرای عملیات...")
                report = await copy_and_send_last_message(user_client, chat_id)
                await bot_client.send_message(chat_id, f"نتیجه عملیات زمان‌بندی:\n{report}")
                await asyncio.sleep(61)
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            print(f"زمان‌بند برای کاربر {chat_id} متوقف شد.")
            break
        except Exception as e:
            print(f"خطا در زمان‌بند برای {chat_id}: {e}")
            await bot_client.send_message(chat_id, f"خطای جدی در زمان‌بندی: {e}")
            await asyncio.sleep(60)


bot = TelegramClient('bot_session', BOT_API_ID, BOT_API_HASH)

def get_main_menu():
    if ACTIVE_USER_SESSION:
        buttons = [
            [Button.text("اجرای دستی عملیات")],
            [Button.text("مدیریت زمان‌بندی"), Button.text("مدیریت قالب پیام")],
            [Button.text("تنظیم کانال‌ها")],
            [Button.text("خروج از حساب")]
        ]
        text = "شما با موفقیت وارد شده‌اید. چه کاری می‌خواهید انجام دهید؟"
    else:
        buttons = [Button.text("شروع فرآیند ورود", resize=True)]
        text = "سلام! برای شروع فرآیند کپی خودکار پیام‌ها، روی دکمه زیر کلیک کنید."
    return text, buttons

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    text, buttons = get_main_menu()
    await event.respond(text, buttons=buttons)
    

@bot.on(events.NewMessage(pattern='شروع فرآیند ورود'))
async def login_handler(event):
    global ACTIVE_USER_SESSION
    if ACTIVE_USER_SESSION:
        return await event.respond("شما از قبل وارد شده‌اید.")

    user_client = None
    try:
        async with bot.conversation(event.chat_id, timeout=300) as conv:
            await conv.send_message("لطفا `API_ID` حساب کاربری خود را وارد کنید.\n\nبرای لغو /cancel را بنویسید.")
            api_id = (await conv.get_response()).text
            if api_id == '/cancel': return await conv.send_message("فرآیند لغو شد.")

            await conv.send_message("عالی! حالا `API_HASH` را وارد کنید.")
            api_hash = (await conv.get_response()).text
            if api_hash == '/cancel': return await conv.send_message("فرآیند لغو شد.")

            await conv.send_message("بسیار خب. شماره تلفن خود را با فرمت بین‌المللی وارد کنید.\nمثال: `+989123456789`")
            phone = (await conv.get_response()).text
            if phone == '/cancel': return await conv.send_message("فرآیند لغو شد.")

            await conv.send_message("در حال تلاش برای اتصال...")
            user_client = TelegramClient(StringSession(), int(api_id), api_hash)
            await user_client.connect()
            
            try:
                code_request = await user_client.send_code_request(phone)
                await conv.send_message(
                    "یک کد به تلگرام شما ارسال شد. لطفاً آن را **به صورت رمزنگاری شده** وارد کنید:\n\n"
                    "**دستورالعمل رمزنگاری:**\n"
                    "به هر رقم از کد ارسال شده **یک واحد اضافه کنید**.\n"
                    "مثال: اگر کد `12345` است، شما باید `23466` را ارسال کنید.\n"
                    "**نکته مهم:** اگر رقمی `9` بود، آن را `0` در نظر بگیرید.\n\n"
                    "برای لغو /cancel را بنویسید."
                )
                encrypted_code = (await conv.get_response()).text
                if encrypted_code == '/cancel': return await conv.send_message("فرآیند لغو شد.")

                decrypted_user_code = decrypt_code(encrypted_code)
                await user_client.sign_in(phone, decrypted_user_code, phone_code_hash=code_request.phone_code_hash)

            except SessionPasswordNeededError:
                await conv.send_message("حساب شما رمز تایید دو مرحله‌ای دارد. لطفاً رمز را وارد کنید.")
                password = (await conv.get_response()).text
                if password == '/cancel': return await conv.send_message("فرآیند لغو شد.")
                await user_client.sign_in(password=password)

            me = await user_client.get_me()
            await conv.send_message(f"ورود موفقیت آمیز بود! خوش آمدید {me.first_name}.")

            user_schedule = DEFAULT_SCHEDULED_TIMES.copy()
            task = asyncio.create_task(scheduler(user_client, bot, event.chat_id, user_schedule))

            ACTIVE_USER_SESSION = {
                'chat_id': event.chat_id, 'client': user_client, 'task': task,
                'schedule': user_schedule, 'template': DEFAULT_MESSAGE_TEMPLATE,
                'source_channel': None,
                'destination_channel': None
            }
            save_user_data()
            
            await conv.send_message("ورود موفق!\n**قدم بعدی:** لطفا از دکمه `تنظیم کانال‌ها` برای مشخص کردن کانال مبدا و مقصد استفاده کنید.")
            
            text, buttons = get_main_menu()
            await conv.send_message(text, buttons=buttons)

    except (PhoneCodeInvalidError, PasswordHashInvalidError):
        await event.respond("خطا: کد یا رمز عبور اشتباه است. لطفاً دوباره تلاش کنید.")
    except Exception as e:
        await event.respond(f"خطا: یک خطای پیش‌بینی نشده رخ داد: {e}\nلطفاً دوباره تلاش کنید.")


@bot.on(events.NewMessage(pattern='تنظیم کانال‌ها'))
async def channel_management_menu_handler(event):
    if not ACTIVE_USER_SESSION:
        return await event.respond(NEEDS_LOGIN_MESSAGE, buttons=get_main_menu()[1])

    buttons = [
        [Button.text("ویرایش کانال‌ها"), Button.text("مشاهده کانال‌ها")],
        [Button.text("بازگشت به منوی اصلی")]
    ]
    text = "از اینجا می‌توانید کانال‌های مبدا و مقصد را مشاهده یا ویرایش کنید."
    await event.respond(text, buttons=buttons)

# جدید: تابع برای مشاهده کانال‌های تنظیم شده
@bot.on(events.NewMessage(pattern='مشاهده کانال‌ها'))
async def view_channels_handler(event):
    if not ACTIVE_USER_SESSION:
        return await event.respond(NEEDS_LOGIN_MESSAGE, buttons=get_main_menu()[1])

    source = ACTIVE_USER_SESSION.get('source_channel', 'تنظیم نشده')
    dest = ACTIVE_USER_SESSION.get('destination_channel', 'تنظیم نشده')

    message = (
        "**کانال‌های فعلی شما:**\n\n"
        f"**کانال مبدا:** `{source}`\n"
        f"**کانال مقصد:** `{dest}`"
    )
    await event.respond(message, parse_mode='md')

@bot.on(events.NewMessage(pattern='ویرایش کانال‌ها'))
async def edit_channels_handler(event):
    if not ACTIVE_USER_SESSION:
        return await event.respond(NEEDS_LOGIN_MESSAGE, buttons=get_main_menu()[1])

    client = ACTIVE_USER_SESSION['client']
    try:
        async with bot.conversation(event.chat_id, timeout=300) as conv:
            await conv.send_message(
                "لطفا شناسه کانال **مبدا** را وارد کنید.\n"
                "می‌توانید از یوزرنیم (مثال: `@my_channel`) یا آیدی عددی (مثال: `-100123456789`) استفاده کنید."
            )
            source_id_str = (await conv.get_response()).text
            if source_id_str == '/cancel': return await conv.send_message("عملیات لغو شد.")

            await conv.send_message("عالی. حالا شناسه کانال **مقصد** را وارد کنید.")
            dest_id_str = (await conv.get_response()).text
            if dest_id_str == '/cancel': return await conv.send_message("عملیات لغو شد.")

            await conv.send_message("در حال بررسی و اعتبارسنجی کانال‌ها...")

            try:
                source_entity_id = int(source_id_str) if source_id_str.lstrip('-').isdigit() else source_id_str
                dest_entity_id = int(dest_id_str) if dest_id_str.lstrip('-').isdigit() else dest_id_str

                await client.get_entity(source_entity_id)
                await client.get_entity(dest_entity_id)

                ACTIVE_USER_SESSION['source_channel'] = source_entity_id
                ACTIVE_USER_SESSION['destination_channel'] = dest_entity_id
                save_user_data()

                await conv.send_message("کانال‌های مبدا و مقصد با موفقیت تنظیم و ذخیره شدند.")
            except Exception as e:
                await conv.send_message(f"**خطا در اعتبارسنجی کانال:**\n`{e}`\n\nلطفا مطمئن شوید شناسه‌ها صحیح هستند و حساب شما در هر دو کانال عضو است.")

    except asyncio.TimeoutError:
        await event.respond("زمان پاسخگویی تمام شد. عملیات لغو شد.")


# ...
def get_template_menu():
    buttons = [[Button.text("نمایش قالب فعلی"), Button.text("ویرایش قالب")], [Button.text("بازگشت به منوی اصلی")]]
    text = "**مدیریت قالب پیام:**\nاز این بخش می‌توانید ظاهر پیام‌های ارسالی را مدیریت کنید."
    return text, buttons

@bot.on(events.NewMessage(pattern='مدیریت قالب پیام'))
async def template_management_handler(event):
    if not ACTIVE_USER_SESSION:
        return await event.respond(NEEDS_LOGIN_MESSAGE, buttons=get_main_menu()[1])
    text, buttons = get_template_menu()
    await event.respond(text, buttons=buttons, parse_mode='md')

@bot.on(events.NewMessage(pattern='نمایش قالب فعلی'))
async def show_template_handler(event):
    if not ACTIVE_USER_SESSION:
        return await event.respond(NEEDS_LOGIN_MESSAGE, buttons=get_main_menu()[1])
    user_template = ACTIVE_USER_SESSION['template']
    await event.respond("قالب فعلی پیام شما:")
    await event.respond(f"{user_template}")

@bot.on(events.NewMessage(pattern='ویرایش قالب'))
async def edit_template_handler(event):
    if not ACTIVE_USER_SESSION:
        return await event.respond(NEEDS_LOGIN_MESSAGE, buttons=get_main_menu()[1])
    try:
        async with bot.conversation(event.chat_id, timeout=600) as conv:
            await conv.send_message("لطفا متن قالب جدید خود را ارسال کنید.\n\n**راهنما:**\n- از `[location]` برای نمایش مکان پروکسی استفاده کنید.\n- از `[link]` برای نمایش لینک اتصال پروکسی استفاده کنید.\n\nبرای لغو /cancel را بنویسید.", parse_mode='md')
            response = await conv.get_response()
            if response.text == '/cancel':
                text, buttons = get_template_menu()
                return await conv.send_message("عملیات لغو شد.", buttons=buttons)

            new_template = response.text
            if '[link]' not in new_template:
                text, buttons = get_template_menu()
                return await conv.send_message("**خطا:** قالب شما باید حتما شامل `[link]` باشد.", buttons=buttons, parse_mode='md')

            ACTIVE_USER_SESSION['template'] = new_template
            save_user_data()
            text, buttons = get_template_menu()
            await conv.send_message("قالب پیام شما با موفقیت به‌روزرسانی شد.", buttons=buttons)
    except asyncio.TimeoutError:
        await event.respond("زمان پاسخگویی تمام شد.")

def get_schedule_menu():
    buttons = [
        [Button.text("افزودن زمان"), Button.text("حذف زمان")],
        [Button.text("نمایش زمان‌ها")],
        [Button.text("بازگشت به منوی اصلی")]
    ]
    return "**مدیریت زمان‌بندی:**\nلطفا یکی از گزینه‌های زیر را انتخاب کنید:", buttons

@bot.on(events.NewMessage(pattern='مدیریت زمان‌بندی'))
async def schedule_management_handler(event):
    if not ACTIVE_USER_SESSION:
        return await event.respond(NEEDS_LOGIN_MESSAGE, buttons=get_main_menu()[1])
    text, buttons = get_schedule_menu()
    await event.respond(text, buttons=buttons, parse_mode='md')

@bot.on(events.NewMessage(pattern='نمایش زمان‌ها'))
async def show_schedule_handler(event):
    if not ACTIVE_USER_SESSION:
        return await event.respond(NEEDS_LOGIN_MESSAGE, buttons=get_main_menu()[1])
    schedule_list = ACTIVE_USER_SESSION.get('schedule', [])
    if not schedule_list:
        return await event.respond("در حال حاضر هیچ زمانی برای ارسال خودکار تنظیم نشده است.")
    
    schedule_list.sort()
    message = "**زمان‌های تنظیم شده برای ارسال خودکار:**\n\n"
    for time in schedule_list:
        message += f"- `{time}`\n"
    await event.respond(message, parse_mode='md')

@bot.on(events.NewMessage(pattern='افزودن زمان'))
async def add_schedule_handler(event):
    if not ACTIVE_USER_SESSION:
        return await event.respond(NEEDS_LOGIN_MESSAGE, buttons=get_main_menu()[1])
    try:
        async with bot.conversation(event.chat_id, timeout=120) as conv:
            await conv.send_message("لطفا زمان جدید را با فرمت `HH:MM` (مثال: `13:45`) وارد کنید.\n\nبرای لغو /cancel را بنویسید.")
            response = await conv.get_response()
            if response.text == '/cancel':
                return await conv.send_message("عملیات لغو شد.")
            new_time = response.text
            if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', new_time):
                return await conv.send_message("**فرمت نامعتبر است.** لطفاً زمان را به شکل `HH:MM` وارد کنید.")
            
            schedule_list = ACTIVE_USER_SESSION['schedule']
            if new_time in schedule_list:
                return await conv.send_message("این زمان از قبل در لیست وجود دارد.")
            
            schedule_list.append(new_time)
            ACTIVE_USER_SESSION['task'].cancel()
            new_task = asyncio.create_task(scheduler(
                ACTIVE_USER_SESSION['client'], bot, ACTIVE_USER_SESSION['chat_id'], schedule_list
            ))
            ACTIVE_USER_SESSION['task'] = new_task
            save_user_data()
            await conv.send_message(f"زمان `{new_time}` با موفقیت به لیست اضافه شد.", parse_mode='md')
    except asyncio.TimeoutError:
        await event.respond("زمان پاسخگویی به پایان رسید. عملیات لغو شد.")

@bot.on(events.NewMessage(pattern='حذف زمان'))
async def delete_schedule_handler(event):
    if not ACTIVE_USER_SESSION:
        return await event.respond(NEEDS_LOGIN_MESSAGE, buttons=get_main_menu()[1])
    try:
        async with bot.conversation(event.chat_id, timeout=120) as conv:
            await conv.send_message("لطفا زمانی که می‌خواهید حذف شود را با فرمت `HH:MM` وارد کنید.\n\nبرای لغو /cancel را بنویسید.")
            response = await conv.get_response()
            if response.text == '/cancel':
                return await conv.send_message("عملیات لغو شد.")
            time_to_delete = response.text
            schedule_list = ACTIVE_USER_SESSION['schedule']
            if time_to_delete not in schedule_list:
                return await conv.send_message(f"زمان `{time_to_delete}` در لیست وجود ندارد.", parse_mode='md')
            
            schedule_list.remove(time_to_delete)
            ACTIVE_USER_SESSION['task'].cancel()
            new_task = asyncio.create_task(scheduler(
                ACTIVE_USER_SESSION['client'], bot, ACTIVE_USER_SESSION['chat_id'], schedule_list
            ))
            ACTIVE_USER_SESSION['task'] = new_task
            save_user_data()
            await conv.send_message(f"زمان `{time_to_delete}` با موفقیت از لیست حذف شد.", parse_mode='md')
    except asyncio.TimeoutError:
        await event.respond("زمان پاسخگویی به پایان رسید. عملیات لغو شد.")

@bot.on(events.NewMessage(pattern='بازگشت به منوی اصلی'))
async def back_to_main_menu_handler(event):
    await start_handler(event)

@bot.on(events.NewMessage(pattern='اجرای دستی عملیات'))
async def manual_run_handler(event):
    if not ACTIVE_USER_SESSION:
        return await event.respond(NEEDS_LOGIN_MESSAGE, buttons=get_main_menu()[1])
    
    await event.respond("در حال اجرای دستی عملیات...")
    user_client = ACTIVE_USER_SESSION['client']
    report = await copy_and_send_last_message(user_client, event.chat_id)
    await event.respond(f"**نتیجه عملیات دستی:**\n{report}", parse_mode='md')

@bot.on(events.NewMessage(pattern='خروج از حساب'))
async def logout_handler(event):
    global ACTIVE_USER_SESSION
    if not ACTIVE_USER_SESSION:
        return await event.respond(NEEDS_LOGIN_MESSAGE, buttons=get_main_menu()[1])
        
    await event.respond("در حال خروج از حساب...")
    ACTIVE_USER_SESSION['task'].cancel()
    await ACTIVE_USER_SESSION['client'].disconnect()
    ACTIVE_USER_SESSION = {}
    delete_user_data()
    text, buttons = get_main_menu()
    await event.respond("شما با موفقیت از حساب خارج شدید.", buttons=buttons)

async def load_active_session_on_startup():
    global ACTIVE_USER_SESSION
    print("در حال بارگیری نشست فعال...")
    user_data = load_user_data()
    if not user_data:
        print("هیچ نشست فعالی یافت نشد.")
        return

    try:
        session_string = user_data['session_string']

        client = TelegramClient(StringSession(session_string), BOT_API_ID, BOT_API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            print("نشست منقضی شده است. فایل حذف می‌شود.")
            delete_user_data()
            return

        my_chat_id = user_data.get('chat_id')
        if not my_chat_id:
            me = await client.get_me()
            my_chat_id = me.id

        schedule = user_data.get('schedule', DEFAULT_SCHEDULED_TIMES.copy())
        template = user_data.get('template', DEFAULT_MESSAGE_TEMPLATE)
        source_channel = user_data.get('source_channel')
        destination_channel = user_data.get('destination_channel')
        
        task = asyncio.create_task(scheduler(client, bot, my_chat_id, schedule))

        ACTIVE_USER_SESSION = {
            'chat_id': my_chat_id, 'client': client, 'task': task,
            'schedule': schedule, 'template': template,
            'source_channel': source_channel, 'destination_channel': destination_channel
        }
        me = await client.get_me()
        print(f"نشست برای کاربر {me.first_name} ({me.id}) با موفقیت بازیابی شد.")
        await bot.send_message(my_chat_id, "ربات با موفقیت ری‌استارت و وارد حساب شما شد.")

    except Exception as e:
        print(f"خطا در بارگیری نشست: {e}. فایل حذف می‌شود.")
        delete_user_data()

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    await load_active_session_on_startup()
    print("ربات شروع به کار کرد...")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    print("ربات در حال اجراست. برای توقف Ctrl+C را فشار دهید.")
    asyncio.run(main())
