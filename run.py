import asyncio
import sys

# 1. CREATE EVENT LOOP BEFORE IMPORTING PYROGRAM
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client, idle, filters
from pyrogram.types import Message

from core import state
from core.handlers import setup_all_handlers
from core.loggers.engine_log import get_logger

log = get_logger("stealth_bot")

async def main():
    app = Client("stealth_bot", api_id=state.API_ID, api_hash=state.API_HASH, bot_token=state.BOT_TOKEN)
    setup_all_handlers(app)
    
    # ─── DIAGNOSTIC RADAR: Catch absolutely everything ───
    @app.on_message(filters.text, group=-1)
    async def catch_all(client, message: Message):
        user_id = message.from_user.id if message.from_user else "Unknown"
        log.info(f"RADAR CAUGHT MESSAGE: '{message.text}' from ID: {user_id}")

    log.info("Test Boot: Connecting to Telegram...")
    await app.start()
    
    # Fetch bot identity to ensure you are talking to the right one
    me = await app.get_me()
    log.info(f"Bot is online! My exact username is: @{me.username}")
    log.info(f"OWNER_ID is configured as: {state.OWNER_ID}")
    log.info("Send 'hello' and then '/dashboard' on Telegram to test.")
    
    await idle()
    await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Shutting down test.")
        sys.exit(0)
