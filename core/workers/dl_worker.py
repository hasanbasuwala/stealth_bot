import asyncio
import json
import urllib.parse

from pyrogram import Client
from core import state

from core.downloader import (
    download_aria2c,
    download_mediago,
    run_custom_workflow,
    download_with_ytdlp,
    extract_fpoxxx_video
)

from .failure import handle_pipeline_failure


async def dl_worker(app: Client):

    while True:

        job_id = await state.dl_queue.get()

        job = state.Job(job_id)

        retry = job.get_state().get("retries", 0)

        try:

            state.ensure_progress(job_id, "Downloading", "Routing")

            meta = json.loads(job.meta_path.read_text())

            url = meta["url"]
            quality = meta.get("quality", "best")

            if "fpo.xxx" in url.lower():
                actual_url, referer, cookie = await extract_fpoxxx_video(
                    url,
                    job_id
                )
            else:
                actual_url, referer, cookie = await run_custom_workflow(
                    url,
                    job_id
                )

            path = urllib.parse.urlparse(actual_url).path.lower()

            if retry == 0:
                await asyncio.to_thread(
                    download_with_ytdlp,
                    actual_url,
                    job_id,
                    referer,
                    cookie,
                    quality,
                    0
                )

            elif retry == 1:
                await asyncio.to_thread(
                    download_with_ytdlp,
                    actual_url,
                    job_id,
                    referer,
                    cookie,
                    quality,
                    1
                )

            elif retry == 2:
                await download_aria2c(actual_url, job_id, job)

            elif retry == 3:
                if ".m3u8" in path:
                    await download_mediago(actual_url, job_id, job)

            else:
                raise Exception("ALL_DOWNLOAD_STRATEGIES_FAILED")

            job.update_state(state.Stage.DOWNLOADED)

            await state.enc_queue.put(job_id)

        except Exception as e:

            retry += 1

            job.write_log(f"Attempt {retry} failed: {e}")

            if retry >= 4:
                await handle_pipeline_failure(app, job, str(e))

            else:
                job.update_state(
                    state.Stage.QUEUED,
                    retries=retry
                )

                await state.dl_queue.put(job_id)

        finally:
            state.dl_queue.task_done()