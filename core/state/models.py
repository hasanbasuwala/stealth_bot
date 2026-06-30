import json
import time
from enum import Enum
from pathlib import Path
from .constants import JOBS_DIR, OWNER_ID
from .memory import _live_progress

class Stage(str, Enum):
    QUEUED      = "queued"
    RESOLVING   = "resolving"
    DOWNLOADING = "downloading"
    DOWNLOADED  = "downloaded"
    ENCODING    = "encoding"
    ENCODED     = "encoded"
    UPLOADING   = "uploading"
    COMPLETED   = "completed"
    FAILED      = "failed"
    CANCELLED   = "cancelled"

class Job:
    def __init__(self, job_id: str):
        self.job_id    = job_id
        self.root      = JOBS_DIR / f"JOB_{job_id}"
        self.dl_dir    = self.root / "dl"
        self.enc_dir   = self.root / "enc"
        self.thumb_dir = self.root / "thumb"

    def init_dirs(self):
        for d in (self.root, self.dl_dir, self.enc_dir, self.thumb_dir):
            d.mkdir(parents=True, exist_ok=True)

    @property
    def meta_path(self)  -> Path: return self.root / "meta.json"
    @property
    def state_path(self) -> Path: return self.root / "state.json"
    @property
    def log_path(self)   -> Path: return self.root / "trace.log"

    def update_state(self, stage: Stage, data: dict = None, retries: int = 0):
        d = json.loads(self.state_path.read_text()) if self.state_path.exists() else {"stage": Stage.QUEUED.value, "retries": 0, "data": {}}
        d["stage"]   = stage.value
        d["retries"] = retries
        if data: d["data"] = data
        self.state_path.write_text(json.dumps(d, indent=2))

    def get_state(self) -> dict:
        if self.state_path.exists():
            try: return json.loads(self.state_path.read_text())
            except Exception: pass
        return {"stage": "unknown", "retries": 0, "data": {}}

    def write_log(self, msg: str):
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

    def check_cancelled(self) -> bool:
        if not self.state_path.exists(): return False
        try: return json.loads(self.state_path.read_text()).get("stage") == Stage.CANCELLED.value
        except Exception: return False

def ensure_progress(job_id: str, default_stage: str, default_status: str):
    if job_id not in _live_progress:
        j    = Job(job_id)
        meta = json.loads(j.meta_path.read_text()) if j.meta_path.exists() else {}
        _live_progress[job_id] = {
            "stage": default_stage, "pct": 0.0,
            "title": meta.get("title", "Media Asset"),
            "status": default_status, "tracker_id": meta.get("tracker_id"),
            "chat_id": meta.get("chat_id", OWNER_ID),
        }
