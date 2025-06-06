import threading
import asyncio
import time
import os
from telethon import TelegramClient, events
from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.types import ReactionEmoji, ChannelParticipantsAdmins


def read_settings():
    status = "off"
    delay = 1
    try:
        with open("settings.txt", "r") as f:
            for line in f:
                if line.startswith("status="):
                    status = line.split("=", 1)[1].strip().lower()
                elif line.startswith("delay="):
                    try:
                        delay = float(line.split("=", 1)[1].strip())
                    except:
                        delay = 1
    except FileNotFoundError:
        pass
    return status, delay


def get_reaction_emoji():
    try:
        with open("reaction.ini", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("reaction="):
                    return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        pass
    return "❤️"


def parse_login_line(line):
    try:
        line = line.replace("'", "").strip()
        api_id, rest = line.split(":", 1)
        api_hash, session_file = rest.split(",", 1)
        return int(api_id.strip()), api_hash.strip(), session_file.strip()
    except Exception as e:
        print(f"Invalid line in login_data.txt: {line}")
        return None


def start_reaction_bot(api_id, api_hash, session_file):
    try:
        client = TelegramClient(session_file, api_id, api_hash)
    except ValueError:
        print(f"Skipping account {api_id} due to invalid session file.")
        return None

    @client.on(events.NewMessage())
    async def handler(event):
        status, delay = read_settings()
        if status != "on":
            return

        if not (event.is_group or event.is_channel):
            return

        sender = await event.get_sender()
        if sender.bot:
            return

        chat = await event.get_chat()
        if chat is None:
            return

        try:
            admins = await client.get_participants(chat, filter=ChannelParticipantsAdmins)
            admin_ids = {admin.id for admin in admins}
        except Exception:
            admin_ids = set()

        if sender.id in admin_ids:
            return

        try:
            await asyncio.sleep(delay)
            emoji = get_reaction_emoji()
            await client(SendReactionRequest(
                peer=await event.get_input_chat(),
                msg_id=event.id,
                reaction=[ReactionEmoji(emoticon=emoji)]
            ))
        except Exception:
            pass

    async def run_client():
        await client.start()
        print(f"[✓] Bot started for {api_id}")
        await client.run_until_disconnected()

    def run_in_thread():
        asyncio.run(run_client())

    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    return thread


def main():
    threads = []
    try:
        with open("login_data.txt", "r") as f:
            lines = f.read().splitlines()
            for line in lines:
                if not line.strip():
                    continue
                parsed = parse_login_line(line)
                if parsed is None:
                    continue
                api_id, api_hash, session_file = parsed

                if not os.path.exists(session_file):
                    print(f"[x] Session file not found: {session_file}")
                    continue

                t = start_reaction_bot(api_id, api_hash, session_file)
                if t is not None:
                    threads.append(t)

        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        print("Exiting...")


if __name__ == "__main__":
    main()
