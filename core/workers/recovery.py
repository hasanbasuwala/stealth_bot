import json
from pyrogram import Client
from core import state

async def recover_pending_jobs(app: Client):
    resumed = []
    if not state.JOBS_DIR.exists(): return
    for folder in state.JOBS_DIR.iterdir():
        if not (folder.is_dir() and folder.name.startswith("JOB_")): continue
        jid  = folder.name.replace("JOB_", "")
        job  = state.Job(jid)
        dl_files = list(job.dl_dir.glob("*")) if job.dl_dir.exists() else []
        has_temp  = any(f.suffix.lower() in [".part", ".ytdl", ".aria2"] for f in dl_files)
        has_solid = any(f.suffix.lower() in [".mp4", ".mkv", ".ts"] for f in dl_files) and not has_temp
        phase = job.get_state().get("stage", "")

        if phase in [state.Stage.COMPLETED.value, state.Stage.FAILED.value, state.Stage.CANCELLED.value]: continue

        meta  = json.loads(job.meta_path.read_text()) if job.meta_path.exists() else {}
        title = meta.get("title", jid)[:20]

        if has_temp or phase in [state.Stage.QUEUED.value, state.Stage.RESOLVING.value, state.Stage.DOWNLOADING.value]:
            job.update_state(state.Stage.QUEUED, retries=0)
            state.dl_queue.put_nowait(jid)
            resumed.append((jid, title))
        elif has_solid or phase in [state.Stage.DOWNLOADED.value, state.Stage.ENCODING.value]:
            job.update_state(state.Stage.DOWNLOADED, retries=0)
            state.enc_queue.put_nowait(jid)
            resumed.append((jid, title))
        elif phase in [state.Stage.ENCODED.value, state.Stage.UPLOADING.value]:
            job.update_state(state.Stage.ENCODED, retries=0)
            state.up_queue.put_nowait(jid)
            resumed.append((jid, title))

    if resumed and state.OWNER_ID:
        lines = "\n".join(f"  • `{title}` (`{jid}`)" for jid, title in resumed)
        try: await app.send_message(state.OWNER_ID, f"🔄 **Boot recovery:** resumed {len(resumed)} job(s)\n{lines}")
        except Exception: pass
