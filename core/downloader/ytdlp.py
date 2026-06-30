import re
import random
import urllib.parse
from pathlib import Path

import yt_dlp
from core import state

IMPERSONATION_POOL = [
    "chrome100",
    "chrome116",
    "edge101",
    "chrome99"
]


def _quality_to_ytdlp_format(quality: str) -> str:
    if quality == "1080":
        return "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
    if quality == "720":
        return "bestvideo[height<=720]+bestaudio/best[height<=720]"
    return "bestvideo+bestaudio/best"


def download_with_ytdlp(
        target_url: str,
        job_id: str,
        referer: str,
        cookie_str: str,
        quality: str = "best",
        attempt: int = 0
) -> Path:

    job = state.Job(job_id)
    out_tmpl = str(job.dl_dir / f"{job_id}.%(ext)s")

    target = IMPERSONATION_POOL[attempt % len(IMPERSONATION_POOL)]

    def progress_hook(d):
        if job.check_cancelled():
            raise ValueError("KILL_SWITCH")

        if d.get("status") == "downloading":
            try:
                if "_percent_str" in d:
                    pct = re.sub(r"\x1b[^m]*m", "", d["_percent_str"])
                    pct = pct.replace("%", "").strip()

                    if job_id in state._live_progress:
                        state._live_progress[job_id]["pct"] = float(pct)
            except:
                pass

    parsed = urllib.parse.urlparse(target_url)

    headers = {
        "Referer": referer,
        "Origin": f"{parsed.scheme}://{parsed.netloc}",
        "User-Agent": state.USER_AGENT
    }

    if cookie_str:
        headers["Cookie"] = cookie_str

    opts = {
        "outtmpl": out_tmpl,
        "format": _quality_to_ytdlp_format(quality),
        "http_headers": headers,
        "progress_hooks": [progress_hook],
        "quiet": True,
        "noplaylist": True,
        "continuedl": True,
        "nocheckcertificate": True,
        "impersonate": target
    }

    job.write_log(f"YT-DLP using {target}")

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(target_url, download=True)

        filename = (
            info.get("requested_downloads", [{}])[0].get("filepath")
            or ydl.prepare_filename(info)
        )

        return Path(filename)