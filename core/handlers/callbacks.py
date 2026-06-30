import json
import shutil
import uuid
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core import state, ui
from core.loggers.engine_log import LOG_FILE

def setup_callbacks(app: Client):
    @app.on_callback_query(filters.user(state.OWNER_ID))
    async def callback_router(_, cb):
        data  = cb.data or ""
        parts = data.split("|")
        action = parts[0]

        if action == "noop":
            await cb.answer()
            return

        if action == "page":
            state._job_list_page = int(parts[1])
            await ui._safe_edit(
                app, state._dashboard_chat_id, state._dashboard_msg_id,
                ui._build_dashboard_text(state._job_list_page), ui._build_dashboard_kb(state._job_list_page)
            )
            await cb.answer()
            return

        if action == "confirm":
            token   = parts[1]
            quality = parts[2]
            pending = state._pending_confirmations.pop(token, None)

            if not pending:
                await cb.answer("Session expired. Paste the URL again.", show_alert=True)
                try: await cb.message.delete()
                except Exception: pass
                return

            if quality == "cancel":
                await cb.answer("Cancelled.")
                try: await cb.message.delete()
                except Exception: pass
                return

            url       = pending["url"]
            chat_id   = pending["chat_id"]
            title_hint = pending.get("title", "Media Asset")

            job_id  = str(uuid.uuid4())[:8]
            tracker = await cb.message.edit_text(
                f"⚡ **{title_hint[:35]}**\n`queued`  ·  `[░░░░░░░░░░]`  0.0%",
                reply_markup=ui._job_tracker_kb(job_id),
            )

            j = state.Job(job_id)
            j.init_dirs()
            j.update_state(state.Stage.QUEUED)
            j.meta_path.write_text(json.dumps({
                "url":        url,
                "title":      title_hint,
                "tracker_id": tracker.id,
                "chat_id":    chat_id,
                "source":     "Direct Paste",
                "quality":    quality,
            }))
            await state.dl_queue.put(job_id)
            await cb.answer(f"Queued at {quality}p ✓")
            return

        if action == "joblog":
            jid      = parts[1]
            log_path = state.JOBS_DIR / f"JOB_{jid}" / "trace.log"
            if not log_path.exists(): log_path = state.DONE_DIR / f"JOB_{jid}" / "trace.log"
            if log_path.exists(): await cb.message.reply_document(str(log_path))
            else: await cb.answer("Log not found.", show_alert=True)
            return

        if action == "kill":
            jid = parts[1]
            state.Job(jid).update_state(state.Stage.CANCELLED)
            if jid in state._active_procs:
                try: state._active_procs[jid].kill()
                except Exception: pass
            shutil.rmtree(state.JOBS_DIR / f"JOB_{jid}", ignore_errors=True)
            state._live_progress.pop(jid, None)
            try: await cb.message.edit_text(f"🛑 **Aborted & wiped:** `{jid}`")
            except Exception: pass
            await cb.answer("Done.")
            return

        if action == "del":
            jid = parts[1]
            shutil.rmtree(state.JOBS_DIR / f"JOB_{jid}", ignore_errors=True)
            shutil.rmtree(state.DONE_DIR / f"JOB_{jid}", ignore_errors=True)
            await cb.answer("Cache cleared.", show_alert=True)
            return

        if action == "ui":
            sub = parts[1]
            if sub == "download":
                await cb.message.reply("📥 **New Download**\nPaste a URL.")
                await cb.answer()
            elif sub == "storage":
                folders = ui._all_job_folders()
                if not folders:
                    await cb.answer("Storage is empty.", show_alert=True)
                    return
                lines = ""
                btns  = []
                for folder in folders[:8]:
                    jid    = folder.name.replace("JOB_", "")
                    meta_f = folder / "meta.json"
                    title  = jid[:8]
                    if meta_f.exists():
                        try: title = json.loads(meta_f.read_text()).get("title", jid)[:28]
                        except Exception: pass
                    mb = sum(f.stat().st_size for f in folder.rglob("*") if f.is_file()) / (1024 ** 2)
                    lines += f"• `{title}` — {mb:.1f} MB\n"
                    btns.append([InlineKeyboardButton(f"🗑 {title[:18]}", callback_data=f"del|{jid}")])
                btns.append([InlineKeyboardButton("← Back", callback_data="ui|back")])
                await cb.message.reply(f"🗂 **Storage**\n\n{lines}", reply_markup=InlineKeyboardMarkup(btns))
                await cb.answer()
            elif sub == "log":
                if LOG_FILE.exists(): await cb.message.reply_document(str(LOG_FILE))
                else: await cb.answer("Log is empty.", show_alert=True)
            elif sub == "clean":
                count = 0
                for folder in ui._all_job_folders():
                    shutil.rmtree(folder, ignore_errors=True)
                    count += 1
                await cb.answer(f"Nuked {count} job folder(s).", show_alert=True)
            else:
                await cb.answer()
            return

        await cb.answer()
