import asyncio
import json
import urllib.parse
from pyrogram import Client
from core import state
from core.downloader import download_aria2c, download_mediago, run_custom_workflow, download_waterfall_fallback
from .failure import handle_pipeline_failure

async def dl_worker(app: Client):
    while True:
        job_id = await state.dl_queue.get()
        job    = state.Job(job_id)
        job_state  = job.get_state()
        retry  = job_state.get("retries", 0)

        try:
            if job.check_cancelled(): raise InterruptedError("KILL_SWITCH")
            state.ensure_progress(job_id, "Downloading", "Routing...")
            job.update_state(state.Stage.DOWNLOADING, retries=retry)

            meta    = json.loads(job.meta_path.read_text())
            url     = meta.get("url")
            source  = meta.get("source")
            quality = meta.get("quality", "best")

            existing = [f for f in job.dl_dir.glob("*") if f.is_file() and f.stat().st_size > 1024 * 1024]
            
            if not existing:
                if "magnet:?" in url:
                    await download_aria2c(url, job_id, job)
                elif source == "telegram":
                    state._live_progress[job_id]["status"] = "Pulling from Telegram..."
                    async def tg_prog(curr, tot):
                        if job_id in state._live_progress:
                            state._live_progress[job_id]["pct"] = (curr * 100 / tot) if tot else 0
                    await app.download_media(meta.get("file_id"), file_name=str(job.dl_dir / f"{job_id}.mp4"), progress=tg_prog)
                else:
                    state._live_progress[job_id]["stage"] = "Resolving"
                    actual_url, referer, cookie_str = await run_custom_workflow(url, job_id)
                    state._live_progress[job_id]["stage"] = "Downloading"

                    clean_path = urllib.parse.urlparse(actual_url).path.lower()
                    
                    # ── SMART ROUTING WITH FALLBACK ──
                    if clean_path.endswith(".m3u8") or "m3u8" in actual_url:
                        try:
                            # Attempt Primary Engine (MediaGo)
                            await download_mediago(actual_url, job_id, job)
                        except Exception as e:
                            # If it's a kill switch, respect it and abort completely
                            if "KILL_SWITCH" in str(e):
                                raise
                            
                            # Log the failure and reroute to Fallback Engine (YT-DLP)
                            job.write_log(f"MediaGo failed ({e}). Rerouting to YT-DLP fallback...")
                            if job_id in state._live_progress:
                                state._live_progress[job_id]["status"] = "MediaGo failed, rerouting..."
                            
                            await asyncio.to_thread(download_waterfall_fallback, actual_url, job_id, referer, cookie_str, quality)

                    elif clean_path.endswith(".mp4") or "direct-mp4" in actual_url:
                        await download_aria2c(actual_url, job_id, job)
                    else:
                        await asyncio.to_thread(download_waterfall_fallback, actual_url, job_id, referer, cookie_str, quality)

            job.update_state(state.Stage.DOWNLOADED, retries=0)
            if job_id in state._live_progress:
                state._live_progress[job_id]["stage"]  = "Wait Process"
                state._live_progress[job_id]["status"] = "Queued for FFmpeg"
            await state.enc_queue.put(job_id)

        except Exception as e:
            if "KILL_SWITCH" not in str(e):
                retry += 1
                job.write_log(f"Download Strike {retry}: {e}")
                if retry >= state.MAX_RETRIES: 
                    await handle_pipeline_failure(app, job, str(e))
                else:
                    job.update_state(state.Stage.QUEUED, retries=retry)
                    await state.dl_queue.put(job_id)
        finally:
            state.dl_queue.task_done()