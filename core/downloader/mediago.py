import asyncio
import re
import subprocess
from pathlib import Path
from core import state

async def download_mediago(m3u8_url: str, job_id: str, job: state.Job) -> Path:
    job.write_log("Spawning MediaGo HLS Engine...")
    out_file = job.dl_dir / f"{job_id}.mp4"
    cmd = ["mediago", "e", "-u", m3u8_url, "-o", str(out_file), "--concurrency", "32"]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=subprocess.STDOUT
    )
    state._active_procs[job_id] = proc
    try:
        while True:
            chunk = await proc.stdout.readline()
            if not chunk: break
            line = chunk.decode("utf-8", errors="ignore")
            if "%" in line and job_id in state._live_progress:
                try:
                    m = re.search(r"(\d+(?:\.\d+)?)%", line)
                    if m: state._live_progress[job_id]["pct"] = float(m.group(1))
                except Exception: pass
    finally:
        await proc.wait()
        state._active_procs.pop(job_id, None)

    if job.check_cancelled(): raise ValueError("KILL_SWITCH_ENGAGED")
    if not out_file.exists() or out_file.stat().st_size < 1024:
        raise RuntimeError("MediaGo failed to produce output.")
    return out_file
