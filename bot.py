import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sys
import os

bot = telebot.TeleBot("7817789571:AAEchI-H-dpetjXcxSkLxz7NURm9yacML4Q")

user_data = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Menu", callback_data="menu"))
    markup.add(InlineKeyboardButton("Developer", url="https://t.me/choudhary"))
    bot.send_message(message.chat.id, "👋 Welcome!", reply_markup=markup)


@bot.message_handler(commands=['login'])
def login_start(message):
    user_data[message.chat.id] = {}
    msg = bot.send_message(message.chat.id, "Please send your API ID (numbers only):")
    bot.register_next_step_handler(msg, process_api_id)

def process_api_id(message):
    if not message.text.isdigit():
        msg = bot.send_message(message.chat.id, "❌ Invalid API ID. Please send numbers only:")
        bot.register_next_step_handler(msg, process_api_id)
        return
    user_data[message.chat.id]['api_id'] = message.text
    msg = bot.send_message(message.chat.id, "Great! Now send your API hash:")
    bot.register_next_step_handler(msg, process_api_hash)

def process_api_hash(message):
    user_data[message.chat.id]['api_hash'] = message.text.strip()
    msg = bot.send_message(message.chat.id, "Almost done! Send your session string:")
    bot.register_next_step_handler(msg, process_session_string)

def process_session_string(message):
    user_data[message.chat.id]['session_string'] = message.text.strip()
    # Save data to a file
    data = user_data[message.chat.id]
    with open("login_data.txt", "a") as f:
        f.write(f"'{data['api_id']}':'{data['api_hash']}','{data['session_string']}'\n")

    bot.send_message(message.chat.id, "✅ Login successful! Your data has been saved securely.")
    user_data.pop(message.chat.id, None)







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
    markup.row(InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/puneet"))
    
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
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📋 Menu", callback_data="menu"),
        InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/puneet")
    )
    bot.send_message(message.chat.id, "👋 Welcome!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "menu")
def handle_menu(call):
    status, delay = get_settings()
    accounts = count_accounts()
    markup = get_menu_markup(status, delay, accounts)
    bot.edit_message_text(
        "📡 Control panel loaded.\nManage your bot settings here.",
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
        "📡 Control panel updated.\nStatus changed successfully.",
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
            "📡 Control panel updated.\nDelay set successfully.",
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
            "📡 Control panel.\nNo delay value entered.",
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
        "📡 Control panel loaded.",
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
    user_data[call.message.chat.id] = {}
    bot.edit_message_text(
        "Please send your API ID (numbers only):",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )
    bot.register_next_step_handler(call.message, process_api_id)

run_both()
