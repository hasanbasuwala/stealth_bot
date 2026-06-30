import json
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core import state, ui

async def handle_pipeline_failure(app: Client, job: state.Job, exception_str: str):
    job.update_state(state.Stage.FAILED, retries=state.MAX_RETRIES)
    job.write_log("CRITICAL: 3 strikes exhausted. Sending crash courier.")

    meta       = json.loads(job.meta_path.read_text()) if job.meta_path.exists() else {}
    chat_id    = meta.get("chat_id", state.OWNER_ID)
    tracker_id = meta.get("tracker_id")

    caption = f"🚨 **Pipeline Crash (3 strikes)**\nJob: `{job.job_id}`\nError: `{exception_str[:200]}`"
    
    if job.log_path.exists():
        try: await app.send_document(chat_id, document=str(job.log_path), caption=caption)
        except Exception: pass
    else:
        try: await app.send_message(chat_id, caption)
        except Exception: pass

    if tracker_id:
        await ui._safe_edit(
            app, chat_id, tracker_id,
            f"❌ **Failed** — `{exception_str[:80]}`",
            InlineKeyboardMarkup([[
                InlineKeyboardButton("📄 Log", callback_data=f"joblog|{job.job_id}"),
                InlineKeyboardButton("🗑 Wipe", callback_data=f"kill|{job.job_id}"),
            ]]),
        )
