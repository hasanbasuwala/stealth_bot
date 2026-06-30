import asyncio
import sys
from pyrogram import Client

from core import state
from core.handlers import setup_all_handlers
from core.loggers.engine_log import get_logger

log = get_logger("stealth_bot")

async def main():
    app = Client("stealth_bot", api_id=state.API_ID, api_hash=state.API_HASH, bot_token=state.BOT_TOKEN)
    setup_all_handlers(app)

    log.info("Test Boot: Connecting to Telegram...")
    async with app:
        log.info("Bot is online! Send /dashboard on Telegram to test the UI.")
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Shutting down test.")
        sys.exit(0)
