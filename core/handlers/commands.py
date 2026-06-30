import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from core import state, ui
from core.loggers.engine_log import get_logger

log = get_logger("handlers")

def setup_commands(app: Client):
    
    @app.on_message(filters.command(["start", "dashboard"]) & filters.user(state.OWNER_ID))
    async def init_dashboard(_, msg: Message):
        log.info(f"Dashboard requested by User ID: {msg.from_user.id}")
        
        state._dashboard_chat_id = msg.chat.id
        m = await msg.reply(
            ui._build_dashboard_text(state._job_list_page),
            reply_markup=ui._build_dashboard_kb(state._job_list_page),
        )
        state._dashboard_msg_id = m.id

    # ── THE WATCHDOG UPDATE COMMAND ──
    @app.on_message(filters.command("update") & filters.user(state.OWNER_ID))
    async def update_bot(_, msg: Message):
        log.info("Update command received. Triggering watchdog.sh...")
        
        await msg.reply("🔄 **Deploying Updates...**\nPulling from GitHub and rebooting. I will be back in ~5 seconds!")
        
        # Launch the watchdog detached so it survives the Python shutdown
        subprocess.Popen(
            ["nohup", "bash", "watchdog.sh"], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL, 
            start_new_session=True
        )
