from pyrogram import Client, filters
from pyrogram.types import Message
from core import state, ui

def setup_commands(app: Client):
    @app.on_message(filters.command(["start", "dashboard"]) & filters.user(state.OWNER_ID))
    async def init_dashboard(_, msg: Message):
        state._dashboard_chat_id = msg.chat.id
        m = await msg.reply(
            ui._build_dashboard_text(state._job_list_page),
            reply_markup=ui._build_dashboard_kb(state._job_list_page),
        )
        state._dashboard_msg_id = m.id
