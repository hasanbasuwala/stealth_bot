import asyncio
import subprocess
from pyrogram import Client
from core import state
from .failure import handle_pipeline_failure

async def enc_worker(app: Client):
    while True:
        job_id = await state.enc_queue.get()
        job    = state.Job(job_id)
        job_state  = job.get_state()
        retry  = job_state.get("retries", 0)

        try:
            if job.check_cancelled(): raise InterruptedError("KILL_SWITCH")
            state.ensure_progress(job_id, "Processing", "FFmpeg Remuxing")
            job.update_state(state.Stage.ENCODING, retries=retry)

            dl_files = [f for f in job.dl_dir.glob("*") if f.is_file()]
            if not dl_files: raise FileNotFoundError("Download dir is empty.")

            dl_file   = max(dl_files, key=lambda p: p.stat().st_size)
            enc_file  = job.enc_dir / f"{job_id}.mp4"
            thumb_file = job.thumb_dir / f"{job_id}.jpg"

            if not enc_file.exists() or enc_file.stat().st_size < 1024:
                await asyncio.create_subprocess_exec(
                    "ffmpeg", "-y", "-i", str(dl_file),
                    "-ss", "00:00:02", "-vframes", "1", str(thumb_file),
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                cmd = [
                    "ffmpeg", "-y", "-nostdin", "-i", str(dl_file),
                    "-c:v", "copy", "-c:a", "aac", "-movflags", "+faststart",
                    str(enc_file),
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                state._active_procs[job_id] = proc
                await proc.wait()
                state._active_procs.pop(job_id, None)

                if job.check_cancelled(): raise ValueError("KILL_SWITCH_ENGAGED")

            job.update_state(state.Stage.ENCODED, retries=0)
            if job_id in state._live_progress:
                state._live_progress[job_id]["stage"]  = "Wait Upload"
                state._live_progress[job_id]["status"] = "Queued for Telegram"
            await state.up_queue.put(job_id)

        except Exception as e:
            if "KILL_SWITCH" not in str(e):
                retry += 1
                job.write_log(f"Encode Strike {retry}: {e}")
                if retry >= state.MAX_RETRIES: await handle_pipeline_failure(app, job, str(e))
                else:
                    job.update_state(state.Stage.DOWNLOADED, retries=retry)
                    await state.enc_queue.put(job_id)
        finally:
            state.enc_queue.task_done()
