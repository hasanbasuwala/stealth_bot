import re
import primp
from core import state

async def run_custom_workflow(url: str, job_id: str) -> tuple[str, str, str]:
    job = state.Job(job_id)
    referer, cookie_str = url, ""

    job.write_log("Firing Native HTTP Scraping Framework...")
    try:
        client = primp.Client(impersonate="chrome_120")
        resp   = client.get(url, headers={"User-Agent": state.USER_AGENT})
        match  = re.search(r"(https?://[^\"']+(?:\.m3u8|\.mp4)[^\"']*)", resp.text)
        if match:
            resolved = match.group(1).replace(r"\/", "/")
            job.write_log("Native Extraction Hit.")
            return resolved, referer, cookie_str
    except Exception as e:
        job.write_log(f"Native parser skipped: {e}")

    job.write_log("Falling back to Playwright headless interceptor...")
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            context = await browser.new_context(user_agent=state.USER_AGENT)
            page    = await context.new_page()

            async def block_bloat(route):
                if route.request.resource_type in ["image", "font", "stylesheet", "media"] or \
                   any(x in route.request.url for x in ["ads", "analytics", "popunder", "tracking"]):
                    await route.abort()
                else:
                    await route.continue_()

            await page.route("**/*", block_bloat)
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            video_src = await page.evaluate("""() => {
                let v = document.querySelector('video');
                if (v && v.src && !v.src.startsWith('blob:')) return v.src;
                let s = document.querySelector('video source');
                if (s && s.src && !s.src.startsWith('blob:')) return s.src;
                return null;
            }""")

            cookies   = await context.cookies()
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
            referer   = page.url
            await browser.close()

            if video_src: return video_src, referer, cookie_str
    except Exception as e:
        job.write_log(f"Playwright fault: {e}")

    return url, referer, cookie_str
