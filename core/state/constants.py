from pathlib import Path
import config

API_ID     = config.API_ID
API_HASH   = config.API_HASH
BOT_TOKEN  = config.BOT_TOKEN
CHANNEL_ID = config.CHANNEL_ID
OWNER_ID   = int(config.OWNER_ID) if hasattr(config, "OWNER_ID") else 0

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
MAX_DL_WORKERS = 3
MAX_RETRIES    = 3

BASE_DIR  = Path("SysCache")
JOBS_DIR  = BASE_DIR / "jobs"
VAULT_DIR = BASE_DIR / "pending_uploads"
DONE_DIR  = BASE_DIR / "completed"
FAIL_DIR  = BASE_DIR / "failed"
BOT_DOWNLOAD_DIR = Path("Bot_Download")

for d in (JOBS_DIR, VAULT_DIR, DONE_DIR, FAIL_DIR, BOT_DOWNLOAD_DIR):
    d.mkdir(parents=True, exist_ok=True)
