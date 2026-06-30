import asyncio
import subprocess

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

dl_queue  = asyncio.Queue()
enc_queue = asyncio.Queue()
up_queue  = asyncio.Queue()

_live_progress: dict[str, dict] = {}
_active_procs: dict[str, subprocess.Process] = {}
_pending_confirmations: dict[str, dict] = {}

_dashboard_msg_id: int = 0
_dashboard_chat_id: int = 0
_job_list_page: int = 0
JOBS_PER_PAGE: int = 4
_last_completed: str = "—"
