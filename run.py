import asyncio
import sys

# 1. CREATE EVENT LOOP BEFORE IMPORTING PYROGRAM
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client, idle

from core import state, ui
from core.workers import recover_pending_jobs, dl_worker, enc_worker, up_worker
from core.handlers import setup_all_handlers
from core.loggers.engine_log import get_logger

log = get_logger("stealth_bot")

async def dashboard_loop(app: Client):
    while True:
        await asyncio.sleep(5)
        # Update individual tracker cards
        for jid, data in list(state._live_progress.items()):
            tid = data.get("tracker_id")
            if tid:
                await ui._safe_edit(
                    app, data.get("chat_id", state.OWNER_ID), tid,
                    ui._job_tracker_text(jid), ui._job_tracker_kb(jid)
                )

        if not state._dashboard_msg_id or not state._dashboard_chat_id:
            continue

        # Update the main dashboard pinned message
        await ui._safe_edit(
            app, state._dashboard_chat_id, state._dashboard_msg_id,
            ui._build_dashboard_text(state._job_list_page),
            ui._build_dashboard_kb(state._job_list_page),
        )

async def terminal_dashboard_loop():
    print("\n" * 6)
    while True:
        await asyncio.sleep(2)
        if not state._live_progress:
            continue
        sys.stdout.write("\033[6A\033[J")
        sys.stdout.write("=== STEALTH BOT — LIVE WORKERS ===\n")
        for jid, data in list(state._live_progress.items())[:5]:
            sys.stdout.write(
                f"[{data.get('title', jid)[:20]}] "
                f"{data.get('stage', '?')} | "
                f"[{ui.make_bar(data.get('pct', 0.0), 8)}] "
                f"{data.get('pct', 0.0):.1f}%\n"
            )
        sys.stdout.flush()

async def main():
    app = Client("stealth_bot", api_id=state.API_ID, api_hash=state.API_HASH, bot_token=state.BOT_TOKEN)
    setup_all_handlers(app)

    log.info("Starting Stealth Bot v12.0 (Fully Decoupled)...")
    async with app:
        await recover_pending_jobs(app)

        # Spin up the background worker threads
        for _ in range(state.MAX_DL_WORKERS):
            asyncio.create_task(dl_worker(app))
        asyncio.create_task(enc_worker(app))
        asyncio.create_task(up_worker(app))
        asyncio.create_task(dashboard_loop(app))
        asyncio.create_task(terminal_dashboard_loop())

        log.info("Stealth Bot v12.0 online! Send a link to test the download pipeline.")
        
        await idle()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Interrupted. Shutting down.")
        sys.exit(0)
