import asyncio
import sys

# 1. CREATE EVENT LOOP BEFORE IMPORTING PYROGRAM
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client, idle

from core import state
from core.handlers import setup_all_handlers
from core.loggers.engine_log import get_logger

log = get_logger("stealth_bot")

async def main():
    app = Client("stealth_bot", api_id=state.API_ID, api_hash=state.API_HASH, bot_token=state.BOT_TOKEN)
    setup_all_handlers(app)

    log.info("Test Boot: Connecting to Telegram...")
    await app.start()
    
    # This will reveal if your config.py is loading the ID correctly!
    log.info(f"Bot is online! OWNER_ID is configured as: {state.OWNER_ID}")
    log.info("Send /dashboard on Telegram to test the UI.")
    
    await idle()
    await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Shutting down test.")
        sys.exit(0)
