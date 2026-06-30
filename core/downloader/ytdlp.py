import re
import urllib.parse
from pathlib import Path
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
from core import state

def _quality_to_ytdlp_format(quality: str) -> str:
    if quality == "1080": return "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
    if quality == "720": return "bestvideo[height<=720]+bestaudio/best[height<=720]"
    return "bestvideo+bestaudio/best"

def download_waterfall_fallback(target_url: str, job_id: str, referer: str, cookie_str: str, quality: str = "best") -> Path:
    job = state.Job(job_id)
    out_tmpl = str(job.dl_dir / f"{job_id}.%(ext)s")

    def prog_hook(d):
        if job.check_cancelled(): raise ValueError("KILL_SWITCH_ENGAGED")
        if d.get("status") == "downloading" and job_id in state._live_progress:
            try:
                clean = re.sub(r"\x1b[^m]*m", "", d.get("_percent_str", "0.0%"))
                state._live_progress[job_id]["pct"] = float(clean.replace("%", "").strip())
            except Exception: pass

    parsed  = urllib.parse.urlparse(target_url)
    headers = {"Referer": referer, "Origin": f"{parsed.scheme}://{parsed.netloc}", "User-Agent": state.USER_AGENT}
    if cookie_str: headers["Cookie"] = cookie_str

    opts = {
        "outtmpl": out_tmpl,
        "format": _quality_to_ytdlp_format(quality),
        "http_headers": headers,
        "progress_hooks": [prog_hook],
        "quiet": True, "no_warnings": True, "noplaylist": True, "continuedl": True, "nocheckcertificate": True,
        # Updated target string below to a supported curl_cffi target
        "impersonate": ImpersonateTarget(client="chrome110"), "compat_opts": {"allow-unsafe-ext"},
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info  = ydl.extract_info(target_url, download=True)
        fname = info.get("requested_downloads", [{}])[0].get("filepath") or ydl.prepare_filename(info)
        return Path(fname)
