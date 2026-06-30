import asyncio
import re
import subprocess
from pathlib import Path
from core import state

async def download_aria2c(url: str, job_id: str, job: state.Job) -> Path:
    job.write_log("Spawning Aria2c Thread Pool Engine...")
    cmd = ["aria2c", "-d", str(job.dl_dir), "-c", "-x", "16", "-s", "10",
           "--seed-time=0", "--summary-interval=0", "--file-allocation=none", url]
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
                    m = re.search(r"\((\d+)%\)", line)
                    if m: state._live_progress[job_id]["pct"] = float(m.group(1))
                except Exception: pass
    finally:
        await proc.wait()
        state._active_procs.pop(job_id, None)

    if job.check_cancelled(): raise ValueError("KILL_SWITCH_ENGAGED")
    files = [f for f in job.dl_dir.rglob("*") if f.is_file() and f.suffix.lower() in [".mp4", ".mkv", ".avi", ".ts", ".webm"]]
    if not files: raise RuntimeError("Aria2c completed but zero media fragments written.")
    return max(files, key=lambda p: p.stat().st_size)
