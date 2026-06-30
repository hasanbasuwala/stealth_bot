import json
import uuid
import urllib.parse
from pyrogram import Client, filters
from pyrogram.types import Message
from core import state, ui

def setup_media(app: Client):
    @app.on_message((filters.video | filters.document) & filters.user(state.OWNER_ID))
    async def auto_catch_media(_, msg: Message):
        if msg.document and msg.document.mime_type and not msg.document.mime_type.startswith("video/"):
            return

        title    = (msg.caption.strip() if msg.caption else "Direct Media Upload")
        job_id   = str(uuid.uuid4())[:8]
        tracker  = await msg.reply(
            f"⚡ **{title[:35]}**\n`queued`  ·  `[░░░░░░░░░░]`  0.0%",
            reply_markup=ui._job_tracker_kb(job_id),
        )

        j = state.Job(job_id)
        j.init_dirs()
        j.update_state(state.Stage.QUEUED)
        j.meta_path.write_text(json.dumps({
            "url":        "telegram_bridge",
            "title":      title,
            "tracker_id": tracker.id,
            "chat_id":    msg.chat.id,
            "source":     "telegram",
            "quality":    "best",
            "file_id":    msg.video.file_id if msg.video else msg.document.file_id,
        }))
        await state.dl_queue.put(job_id)
        try: await msg.delete()
        except Exception: pass

    @app.on_message(filters.text & filters.user(state.OWNER_ID) & ~filters.command(["start", "dashboard"]))
    async def native_link_catcher(_, msg: Message):
        url = next((w for w in msg.text.split() if w.startswith("http") or w.startswith("magnet:?")), None)
        if not url: return

        title_hint = msg.text.replace(url, "").strip() or urllib.parse.urlparse(url).netloc or url[:40]
        await ui._send_confirm_card(app, msg.chat.id, url, title_hint)
