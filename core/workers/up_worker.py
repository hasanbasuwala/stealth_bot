import asyncio
import json
import shutil
import subprocess
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core import state, ui
from .failure import handle_pipeline_failure

async def up_worker(app: Client):
    while True:
        job_id = await state.up_queue.get()
        job    = state.Job(job_id)
        job_state  = job.get_state()
        retry  = job_state.get("retries", 0)

        try:
            if job.check_cancelled(): raise InterruptedError("KILL_SWITCH")
            state.ensure_progress(job_id, "Uploading", "Deploying...")
            job.update_state(state.Stage.UPLOADING, retries=retry)

            enc_file   = job.enc_dir / f"{job_id}.mp4"
            thumb_file = job.thumb_dir / f"{job_id}.jpg"
            meta       = json.loads(job.meta_path.read_text())
            tracker_id = meta.get("tracker_id")
            chat_target = meta.get("chat_id", state.OWNER_ID)

            w, h, dur = 1280, 720, 100
            try:
                proc = await asyncio.create_subprocess_exec(
                    "ffprobe", "-v", "error",
                    "-show_entries", "stream=width,height:format=duration",
                    "-of", "json", str(enc_file),
                    stdout=subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
                probe = json.loads(stdout.decode())
                dur   = int(float(probe.get("format", {}).get("duration", 100)))
                for s in probe.get("streams", []):
                    if s.get("width"): w, h = s["width"], s["height"]
            except Exception: pass

            async def up_prog(curr, tot):
                if job_id in state._live_progress:
                    state._live_progress[job_id]["pct"] = (curr * 100 / tot) if tot else 0

            await app.send_video(
                state.CHANNEL_ID,
                video=str(enc_file),
                thumb=str(thumb_file) if thumb_file.exists() else None,
                caption=meta.get("title", "Asset"),
                width=w, height=h, duration=dur,
                supports_streaming=True,
                progress=up_prog,
            )

            state._last_completed = meta.get("title", job_id)[:40]
            job.update_state(state.Stage.COMPLETED)

            if tracker_id:
                await ui._safe_edit(
                    app, chat_target, tracker_id,
                    f"✅ **Done** — `{meta.get('title', '')[:40]}`",
                    InlineKeyboardMarkup([[
                        InlineKeyboardButton("📄 Log", callback_data=f"joblog|{job_id}"),
                        InlineKeyboardButton("🗑 Delete Cache", callback_data=f"del|{job_id}"),
                    ]]),
                )

            state._live_progress.pop(job_id, None)
            try: shutil.move(str(job.root), str(state.DONE_DIR / job.root.name))
            except Exception: pass

        except Exception as e:
            if "KILL_SWITCH" not in str(e):
                retry += 1
                job.write_log(f"Upload Strike {retry}: {e}")
                if retry >= state.MAX_RETRIES: await handle_pipeline_failure(app, job, str(e))
                else:
                    job.update_state(state.Stage.ENCODED, retries=retry)
                    await state.up_queue.put(job_id)
        finally:
            state.up_queue.task_done()
