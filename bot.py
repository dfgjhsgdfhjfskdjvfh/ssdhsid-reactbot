import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sys
import os
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
import asyncio

bot = telebot.TeleBot("7152505927:AAFssTXF2zBPeLu1Mmvp61LNgPW6-b28A7Y")

user_data = {}
login_sessions = {}

def generate_keypad(code):
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("Show code", url="https://t.me/+42777"))
    digits = [
        ["1️⃣", "2️⃣", "3️⃣"],
        ["4️⃣", "5️⃣", "6️⃣"],
        ["7️⃣", "8️⃣", "9️⃣"],
        ["0️⃣"]
    ]
    for row in digits:
        buttons = [InlineKeyboardButton(d, callback_data=d) for d in row]
        keyboard.row(*buttons)
    return keyboard

emoji_to_digit = {
    "0️⃣": "0", "1️⃣": "1", "2️⃣": "2", "3️⃣": "3", "4️⃣": "4",
    "5️⃣": "5", "6️⃣": "6", "7️⃣": "7", "8️⃣": "8", "9️⃣": "9"
}


@bot.message_handler(commands=['login'])
def start_login(message):
    uid = str(message.from_user.id)
    login_sessions[uid] = {"stage": "ask_api_id"}
    bot.send_message(message.chat.id, "Please send your API ID (a number):")

@bot.message_handler(func=lambda message: str(message.from_user.id) in login_sessions and login_sessions[str(message.from_user.id)].get("stage") in ["ask_api_id", "ask_api_hash", "ask_phone", "waiting_2fa"])
def handle_login_messages(message):
    uid = str(message.from_user.id)
    session = login_sessions.get(uid)

    if not session:
        return

    stage = session.get("stage")

    if stage == "ask_api_id":
        if message.text and message.text.isdigit():
            session["api_id"] = int(message.text)
            session["stage"] = "ask_api_hash"
            bot.send_message(message.chat.id, "Great! Now send your API HASH (a string):")
        else:
            bot.send_message(message.chat.id, "API ID should be a number. Please send your API ID:")

    elif stage == "ask_api_hash":
        if message.text and len(message.text) >= 10:
            session["api_hash"] = message.text.strip()
            session["stage"] = "ask_phone"
            bot.send_message(message.chat.id, "Now send your mobile phone number in international format (e.g., +1234567890):")
        else:
            bot.send_message(message.chat.id, "API HASH looks invalid. Please send your API HASH:")

    elif stage == "ask_phone":
        phone = message.text.strip() if message.text else ""
        if phone.startswith('+') and len(phone) > 5:
            session["phone"] = phone
            session["code"] = ""
            session["sent"] = False
            session["2fa"] = False
            session["stage"] = "waiting_code"
            asyncio.run(initiate_login(session, uid, message))
        else:
            bot.send_message(message.chat.id, "Please send a valid phone number starting with '+'.")

    elif stage == "waiting_2fa":
        if session.get("2fa"):
            password = message.text.strip()
            asyncio.run(attempt_2fa(session, uid, message, password))
        else:
            bot.send_message(message.chat.id, "Please wait for the login process or send /login to restart.")

async def initiate_login(session, uid, message):
    api_id = session["api_id"]
    api_hash = session["api_hash"]
    phone = session["phone"]
    chat_id = message.chat.id

    try:
        client = TelegramClient(str(api_id), api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            code_info = await client.send_code_request(phone)
            session["phone_code_hash"] = code_info.phone_code_hash
            session["sent"] = True
            msg = bot.send_message(
                chat_id,
                f"Login code has been sent to your Telegram account linked with {phone}.\nEnter code using the buttons below or type manually:",
                reply_markup=generate_keypad("")
            )
            session["msg_id"] = msg.message_id
            session["chat_id"] = chat_id
        await client.disconnect()
    except Exception as e:
        bot.send_message(chat_id, f"Error sending code: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data in emoji_to_digit)
def handle_keypad(call):
    uid = str(call.from_user.id)
    session = login_sessions.get(uid)
    if not session or session.get("2fa") or session.get("stage") != "waiting_code":
        return

    digit = emoji_to_digit[call.data]

    if len(session["code"]) >= 5:
        return

    session["code"] += digit
    updated_text = f"Login code has been sent to your Telegram account linked with {session['phone']}.\nEnter code: {session['code']}"

    try:
        bot.edit_message_text(
            updated_text,
            chat_id=session["chat_id"],
            message_id=session["msg_id"],
            reply_markup=generate_keypad(session["code"])
        )
    except Exception:
        pass

    if len(session["code"]) == 5:
        asyncio.run(complete_login(session, uid))

async def complete_login(session, uid):
    api_id = session["api_id"]
    api_hash = session["api_hash"]
    phone = session["phone"]
    code = session["code"]
    chat_id = session["chat_id"]
    phone_code_hash = session.get("phone_code_hash")

    try:
        client = TelegramClient(str(api_id), api_id, api_hash)
        await client.connect()
        await client.sign_in(phone, code=code, phone_code_hash=phone_code_hash)
        bot.send_message(chat_id, "✅ Done! You are now logged in.")
        session["stage"] = "logged_in"
        save_login_data(api_id, api_hash)
        await client.disconnect()
    except SessionPasswordNeededError:
        session["2fa"] = True
        session["stage"] = "waiting_2fa"
        try:
            bot.delete_message(chat_id, session["msg_id"])
        except Exception:
            pass
        bot.send_message(chat_id, "✅ Please enter your two-factor authentication password:")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Login failed: {str(e)}")
        session["code"] = ""
        session["stage"] = "waiting_code"

async def attempt_2fa(session, uid, message, password):
    api_id = session["api_id"]
    api_hash = session["api_hash"]
    chat_id = message.chat.id

    try:
        client = TelegramClient(str(api_id), api_id, api_hash)
        await client.connect()
        await client.sign_in(password=password)
        bot.send_message(chat_id, "✅ Logged in successfully with 2FA!")
        session["2fa"] = False
        session["stage"] = "logged_in"
        save_login_data(api_id, api_hash)
        await client.disconnect()
    except Exception as e:
        bot.send_message(chat_id, f"❌ 2FA Login failed: {str(e)}")

def save_login_data(api_id, api_hash):
    session_file = f"{api_id}.session"
    line = f"'{api_id}':'{api_hash}','{session_file}'\n"
    with open("login_data.txt", "a") as f:
        f.write(line)

def get_settings():
    status = "off"
    delay = "0"
    try:
        with open("settings.txt", "r") as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                if line:  # Skip empty lines
                    key, value = line.split('=', 1)
                    if key == "status":
                        status = value
                    elif key == "delay":
                        delay = value
    except FileNotFoundError:
        # Create default settings file if it doesn't exist
        with open("settings.txt", "w") as f:
            f.write("status=off\ndelay=0\n")
    return status, delay

def update_status(new_status):
    current_status, current_delay = get_settings()
    with open("settings.txt", "w") as f:
        f.write(f"status={new_status}\n")
        f.write(f"delay={current_delay}\n")

def count_accounts():
    try:
        with open("login_data.txt", "r") as f:
            return len(f.readlines())
    except:
        return 0

def get_current_reaction():
    try:
        with open("reaction.ini", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("reaction="):
                    return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        return "👍"  # Default reaction
    return "👍"  # Default if no reaction found in file

def get_menu_markup(status, delay, accounts):
    if status.lower() == "on":
        status_button = InlineKeyboardButton("✅ Working", callback_data="toggle_status")
    else:
        status_button = InlineKeyboardButton("⛔ Stopped", callback_data="toggle_status")

    current_reaction = get_current_reaction()
    markup = InlineKeyboardMarkup()
    
    # Status button in first row
    markup.row(status_button)
    
    # Reaction and Add Account in second row
    markup.row(
        InlineKeyboardButton(f"{current_reaction} Reaction", callback_data="reactions"),
        InlineKeyboardButton(f"👥 Accounts: {accounts}", callback_data="accounts")
    )
    
    # Add and Delete Account in third row
    markup.row(
        InlineKeyboardButton("➕ New Account", callback_data="new_account"),
        InlineKeyboardButton("🗑️ Delete Account", callback_data="delete_account")
    )
    
    # Delay in fourth row
    markup.row(InlineKeyboardButton(f"⏱️ Delay: {delay}", callback_data="delay"))

    markup.row(InlineKeyboardButton("🔁 Restart", callback_data="exit_program"))
    
    # Developer in last row
    markup.row(InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/choudhary"))
    
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "exit_program")
def handle_callbacks(call):
    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🔁 Program Restarted.\n\nSend /start to hit me up again."
        )
    except Exception:
        pass  # Avoid any issues if editing fails

    print("Exiting program...")
    os._exit(0)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    username = f"@{user.username}" if user.username else "None"
    user_id = user.id
    language_code = user.language_code or "Unknown"
    is_bot = "Yes" if user.is_bot else "No"

    welcome_text = (
        "👋 **Welcome to the Bot!**\n\n"
        "🧾 **Your Info:**\n"
        "├─ 👤 Name        : `{}`\n"
        "├─ 🔗 Username    : `{}`\n"
        "├─ 🆔 User ID     : `{}`\n"
        "├─ 🌐 Language    : `{}`\n"
        "└─ 🤖 Is Bot      : `{}`\n\n"
        "📌 Use the buttons below to get started."
    ).format(full_name, username, user_id, language_code, is_bot)

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📋 Menu", callback_data="menu"),
        InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/choudhary")
    )

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data == "menu")
def handle_menu(call):
    status, delay = get_settings()
    accounts = count_accounts()
    markup = get_menu_markup(status, delay, accounts)
    bot.edit_message_text(
        "⚙️ Control panel loaded.\nManage your bot settings here.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "toggle_status")
def toggle_status(call):
    current_status, delay = get_settings()
    new_status = "off" if current_status == "on" else "on"
    update_status(new_status)
    accounts = count_accounts()
    markup = get_menu_markup(new_status, delay, accounts)
    bot.edit_message_text(
        "⚙️ Control panel updated.\nStatus changed successfully.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

def get_numeric_keypad_markup(current_input=""):
    markup = InlineKeyboardMarkup()
    # Add message showing current input
    numbers = [
        ["1", "2", "3"],
        ["4", "5", "6"],
        ["7", "8", "9"],
        ["0", "✅"]
    ]
    
    for row in numbers[:-1]:  # Handle all rows except the last one
        markup.row(
            *[InlineKeyboardButton(num, callback_data=f"delay_num_{num}") for num in row]
        )
    
    # Handle last row specially
    markup.row(
        InlineKeyboardButton(numbers[-1][0], callback_data=f"delay_num_{numbers[-1][0]}"),
        InlineKeyboardButton(numbers[-1][1], callback_data="delay_confirm")
    )
    
    return markup

def update_delay(new_delay):
    current_status, _ = get_settings()
    with open("settings.txt", "w") as f:
        f.write(f"status={current_status}\n")
        f.write(f"delay={new_delay}\n")

@bot.callback_query_handler(func=lambda call: call.data == "delay")
def handle_delay(call):
    bot.edit_message_text(
        "Enter the time:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=get_numeric_keypad_markup()
    )
    # Initialize the input buffer for this user
    user_data[call.message.chat.id] = {"delay_input": ""}

@bot.callback_query_handler(func=lambda call: call.data.startswith("delay_num_"))
def handle_delay_number(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        user_data[chat_id] = {"delay_input": ""}
    
    number = call.data.split("_")[-1]
    user_data[chat_id]["delay_input"] += number
    
    bot.edit_message_text(
        f"Enter the time: {user_data[chat_id]['delay_input']}",
        chat_id=chat_id,
        message_id=call.message.message_id,
        reply_markup=get_numeric_keypad_markup()
    )

@bot.callback_query_handler(func=lambda call: call.data == "delay_confirm")
def handle_delay_confirm(call):
    chat_id = call.message.chat.id
    if chat_id in user_data and "delay_input" in user_data[chat_id]:
        new_delay = user_data[chat_id]["delay_input"]
        update_delay(new_delay)
        # Clear the input buffer
        user_data[chat_id].pop("delay_input", None)
        
        # Return to main menu
        status, delay = get_settings()
        accounts = count_accounts()
        markup = get_menu_markup(status, delay, accounts)
        bot.edit_message_text(
            "⚙️ Control panel updated.\nDelay set successfully.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
    else:
        # Handle case where no input was provided
        status, delay = get_settings()
        accounts = count_accounts()
        markup = get_menu_markup(status, delay, accounts)
        bot.edit_message_text(
            "⚙️ Control panel.\nNo delay value entered.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )

def get_accounts():
    accounts = []
    try:
        with open("login_data.txt", "r") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) >= 1:
                    api_id = parts[0].strip("'")
                    accounts.append(api_id)
    except FileNotFoundError:
        pass
    return accounts

def delete_account(api_id):
    accounts = []
    try:
        with open("login_data.txt", "r") as f:
            accounts = f.readlines()
    except FileNotFoundError:
        return False

    with open("login_data.txt", "w") as f:
        for account in accounts:
            if not account.startswith(f"'{api_id}':"):
                f.write(account)
    return True

def get_account_list_markup():
    markup = InlineKeyboardMarkup()
    accounts = get_accounts()
    
    for api_id in accounts:
        markup.row(
            InlineKeyboardButton(f"API ID: {api_id}", callback_data=f"account_info_{api_id}"),
            InlineKeyboardButton("❌", callback_data=f"delete_account_{api_id}")
        )
    
    markup.row(InlineKeyboardButton("✅ Done", callback_data="back_to_menu"))
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "delete_account")
def handle_delete_account(call):
    markup = get_account_list_markup()
    bot.edit_message_text(
        "Select an account to delete:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_account_"))
def handle_account_deletion(call):
    api_id = call.data.split("_")[-1]
    if delete_account(api_id):
        markup = get_account_list_markup()
        bot.edit_message_text(
            f"Account with API ID {api_id} deleted successfully!\n\nRemaining accounts:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
    else:
        markup = get_account_list_markup()
        bot.edit_message_text(
            "Failed to delete account. Please try again.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def handle_back_to_menu(call):
    status, delay = get_settings()
    accounts = count_accounts()
    markup = get_menu_markup(status, delay, accounts)
    bot.edit_message_text(
        "⚙️ Control panel loaded.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

import threading
import subprocess

def run_reactor_script():
    subprocess.run(['python', 'reactor.py'])

def run_both():
    reactor_thread = threading.Thread(target=run_reactor_script)
    reactor_thread.daemon = True
    reactor_thread.start()

    bot.polling()

def get_reaction_keyboard():
    emojis = [
        ["👍", "🖕", "😂", "🤝", "👏", "👎", "❤️", "👉"],
        ["🔥", "🥰", "😄", "😅", "🤯", "😱", "🤬", "😢"],
        ["🎉", "🤩", "🤮", "💩", "🙏", "👌", "🕊", "🤡"],
        ["⚡", "🍌", "🏆", "💔", "😐", "😑", "🍓", "🍾"],
        ["💋", "😈", "😴", "😭", "🤓", "👻", "👨‍💻", "👀"],
        ["🎃", "🙈", "😇", "🙂", "✍", "😊", "🎅", "🎄"],
        ["☃️", "💅", "😜", "🗿", "🆒", "💘", "🙉", "🦄"],
        ["😘", "💊", "🙈", "😎", "👾", "🤷‍♂️", "🤷‍♀️", "🤷"],
        ["😡"]
    ]
    
    markup = InlineKeyboardMarkup()
    for row in emojis:
        buttons = [InlineKeyboardButton(emoji, callback_data=f"set_reaction_{emoji}") for emoji in row]
        markup.row(*buttons)
    markup.row(InlineKeyboardButton("🔙 Back", callback_data="back_to_menu"))
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "reactions")
def handle_reactions(call):
    markup = get_reaction_keyboard()
    bot.edit_message_text(
        "Select an emoji to react:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_reaction_"))
def handle_set_reaction(call):
    emoji = call.data.replace("set_reaction_", "")
    try:
        with open("reaction.ini", "w", encoding="utf-8") as f:
            f.write(f"reaction={emoji}\n")
        
        status, delay = get_settings()
        accounts = count_accounts()
        markup = get_menu_markup(status, delay, accounts)
        bot.edit_message_text(
            f"✅ Reaction emoji set to {emoji}\nControl panel loaded.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "new_account")
def handle_new_account(call):
    uid = str(call.from_user.id)
    login_sessions[uid] = {"stage": "ask_api_id"}
    bot.edit_message_text(
        "Please send your API ID (numbers only):",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

run_both()
