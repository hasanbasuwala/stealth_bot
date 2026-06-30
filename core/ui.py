import asyncio
import json
import uuid
import urllib.parse
from pathlib import Path
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, MessageNotModified
from core import state

def make_bar(percent: float, width: int = 10) -> str:
    filled = int(max(0.0, min(percent, 100.0)) / (100.0 / width))
    return "█" * filled + "░" * (width - filled)

def _job_tracker_text(job_id: str) -> str:
    data  = state._live_progress.get(job_id, {})
    stage = data.get("stage", "Working")
    pct   = data.get("pct", 0.0)
    title = data.get("title", job_id)[:35]
    bar   = make_bar(pct)
    return f"⚡ **{title}**\n`{stage}`  ·  `[{bar}]`  {pct:.1f}%"

def _job_tracker_kb(job_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📄 Log", callback_data=f"joblog|{job_id}"),
        InlineKeyboardButton("🛑 Abort", callback_data=f"kill|{job_id}"),
    ]])

async def _safe_edit(app: Client, chat_id: int, msg_id: int, text: str, kb: InlineKeyboardMarkup = None):
    try: await app.edit_message_text(chat_id, msg_id, text, reply_markup=kb)
    except MessageNotModified: pass
    except FloodWait as e: await asyncio.sleep(e.value)
    except Exception: pass

def _storage_mb() -> float:
    return sum(f.stat().st_size for f in state.JOBS_DIR.rglob("*") if f.is_file()) / (1024 ** 2)

def _all_job_folders() -> list[Path]:
    if not state.JOBS_DIR.exists(): return []
    return sorted([d for d in state.JOBS_DIR.iterdir() if d.is_dir() and d.name.startswith("JOB_")], key=lambda p: p.stat().st_mtime, reverse=True)

def _build_dashboard_text(page: int) -> str:
    active_count = len(state._live_progress)
    wait_enc  = state.enc_queue.qsize()
    wait_up   = state.up_queue.qsize()
    storage   = _storage_mb()

    sys_status = "🟢 Idle" if (active_count == 0 and wait_enc == 0 and wait_up == 0) else f"🔵 Busy  ({active_count} active)"
    active_lines = "".join([f"  `{data.get('title', jid)[:22]}`\n  `[{make_bar(data.get('pct', 0.0), 8)}]` {data.get('pct', 0.0):.1f}%  _{data.get('stage', 'Working')}_\n" for jid, data in state._live_progress.items()]) or "  _Nothing running_\n"
    queue_lines = f"  Waiting to encode : `{wait_enc}`\n  Waiting to upload : `{wait_up}`\n"

    all_folders = _all_job_folders()
    total_jobs  = len(all_folders)
    total_pages = max(1, (total_jobs + state.JOBS_PER_PAGE - 1) // state.JOBS_PER_PAGE)
    safe_page   = max(0, min(page, total_pages - 1))

    job_lines = ""
    for folder in all_folders[safe_page * state.JOBS_PER_PAGE : (safe_page + 1) * state.JOBS_PER_PAGE]:
        jid = folder.name.replace("JOB_", "")
        title, stage = jid[:8], "?"
        if (folder / "meta.json").exists():
            try: title = json.loads((folder / "meta.json").read_text()).get("title", jid)[:28]
            except Exception: pass
        if (folder / "state.json").exists():
            try: stage = json.loads((folder / "state.json").read_text()).get("stage", "?")
            except Exception: pass
        job_lines += f"  • `{title}`  _{stage}_\n"
    
    if not job_lines: job_lines = "  _No jobs on disk_\n"

    return (
        f"🖥  **STEALTH BOT DASHBOARD**\n{'─' * 30}\n\n"
        f"**Status**\n{sys_status}\n\n"
        f"**Active  ({active_count})**\n{active_lines}\n"
        f"**Queued**\n{queue_lines}\n"
        f"**All Jobs** (page {safe_page + 1}/{total_pages})\n{job_lines}\n"
        f"**Last Completed**\n  `{state._last_completed[:40]}`\n\n"
        f"**Storage** `{storage:.1f} MB`  in  `{total_jobs}` job folder(s)"
    )

def _build_dashboard_kb(page: int) -> InlineKeyboardMarkup:
    total_jobs  = len(_all_job_folders())
    total_pages = max(1, (total_jobs + state.JOBS_PER_PAGE - 1) // state.JOBS_PER_PAGE)
    safe_page   = max(0, min(page, total_pages - 1))

    prev_btn = InlineKeyboardButton("◀ Prev", callback_data=f"page|{safe_page - 1}") if safe_page > 0 else InlineKeyboardButton("·", callback_data="noop")
    next_btn = InlineKeyboardButton("Next ▶", callback_data=f"page|{safe_page + 1}") if safe_page < total_pages - 1 else InlineKeyboardButton("·", callback_data="noop")

    return InlineKeyboardMarkup([
        [prev_btn, InlineKeyboardButton(f"{safe_page + 1}/{total_pages}", callback_data="noop"), next_btn],
        [InlineKeyboardButton("📥 New Download", callback_data="ui|download"), InlineKeyboardButton("🗂 Storage", callback_data="ui|storage")],
        [InlineKeyboardButton("📄 System Log", callback_data="ui|log"), InlineKeyboardButton("🧹 Nuke Cache", callback_data="ui|clean")],
    ])

async def _send_confirm_card(app: Client, chat_id: int, url: str, title_hint: str) -> None:
    token = str(uuid.uuid4())[:8]
    state._pending_confirmations[token] = {"url": url, "chat_id": chat_id, "title": title_hint}
    domain = urllib.parse.urlparse(url).netloc or url[:30]
    
    text = f"🔗 **New Download**\n{'─' * 28}\n**Source:** `{domain}`\n**Title:** `{title_hint[:45]}`\n\nPick a quality to queue, or cancel:"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📺 1080p", callback_data=f"confirm|{token}|1080"), InlineKeyboardButton("📺 720p", callback_data=f"confirm|{token}|720")],
        [InlineKeyboardButton("✖ Cancel", callback_data=f"confirm|{token}|cancel")],
    ])
    await app.send_message(chat_id, text, reply_markup=kb)
