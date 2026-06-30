import re
import primp
from core import state


async def run_custom_workflow(url: str, job_id: str):

    job = state.Job(job_id)

    referer = url
    cookie_str = ""

    if ".m3u8" in url.lower() or ".mp4" in url.lower():
        job.write_log("Direct media detected")
        return url, referer, cookie_str

    try:
        job.write_log("Trying primp extraction")

        client = primp.Client(impersonate="chrome_120")

        resp = client.get(
            url,
            headers={"User-Agent": state.USER_AGENT},
            timeout=20
        )

        if resp.status_code == 200:

            match = re.search(
                r"(https?://[^\"']+(?:\.m3u8|\.mp4)[^\"']*)",
                resp.text
            )

            if match:
                resolved = match.group(1).replace(r"\/", "/")
                job.write_log("primp extraction success")

                return resolved, referer, cookie_str

    except Exception as e:
        job.write_log(f"primp failed: {e}")

    try:
        job.write_log("Escalating to Playwright")

        from playwright.async_api import async_playwright

        async with async_playwright() as p:

            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox"]
            )

            context = await browser.new_context(
                user_agent=state.USER_AGENT
            )

            page = await context.new_page()

            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000
            )

            video = await page.evaluate("""
                () => {
                    let v = document.querySelector("video");
                    if (v && v.src) return v.src;
                    return null;
                }
            """)

            cookies = await context.cookies()

            cookie_str = "; ".join(
                [f"{c['name']}={c['value']}" for c in cookies]
            )

            referer = page.url

            await browser.close()

            if video:
                return video, referer, cookie_str

    except Exception as e:
        job.write_log(f"Playwright failed: {e}")

    return url, referer, cookie_str