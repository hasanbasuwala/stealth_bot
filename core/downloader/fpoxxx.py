import re
from playwright.async_api import async_playwright
from core import state

async def extract_fpoxxx_video(url: str, job_id: str) -> tuple[str, str, str]:
    job = state.Job(job_id)
    referer, cookie_str = url, ""
    
    job.write_log("Firing Dedicated FPOXXX Scraper...")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            context = await browser.new_context(user_agent=state.USER_AGENT)
            page    = await context.new_page()

            # Block heavy ads/tracking to make extraction instant
            async def block_bloat(route):
                if route.request.resource_type in ["image", "font", "stylesheet"] or \
                   any(x in route.request.url for x in ["ads", "analytics", "popunder", "tracking", "banner"]):
                    await route.abort()
                else:
                    await route.continue_()

            await page.route("**/*", block_bloat)
            
            # Load the video detail page
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Extract the raw media URL from the player or metadata
            video_src = await page.evaluate("""() => {
                // 1. Try standard HTML5 video tag
                let v = document.querySelector('video');
                if (v && v.src && !v.src.startsWith('blob:')) return v.src;
                
                // 2. Try nested source tag
                let s = document.querySelector('video source');
                if (s && s.src && !s.src.startsWith('blob:')) return s.src;
                
                // 3. Try OpenGraph metadata fallback
                let og = document.querySelector('meta[property="og:video"]');
                if (og && og.content) return og.content;
                
                return null;
            }""")

            # Capture cookies required to download the video file
            cookies = await context.cookies()
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
            referer = page.url
            await browser.close()

            if video_src:
                job.write_log(f"FPOXXX extraction successful: {video_src[:50]}...")
                return video_src, referer, cookie_str
            else:
                job.write_log("FPOXXX extractor failed to find video element. Falling back...")
                
    except Exception as e:
        job.write_log(f"FPOXXX Playwright fault: {e}")

    # Fallback to the original URL if something goes wrong
    return url, referer, cookie_str