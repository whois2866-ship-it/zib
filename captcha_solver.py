"""
CAPTCHA solving module using CapSolver API.
TikTok uses FunCaptcha (Arkose Labs) for signup protection.
"""

import asyncio
import httpx
from config import Config
from logger import log


class CaptchaSolver:
    BASE_URL = "https://api.capsolver.com"

    def __init__(self):
        self.api_key = Config.CAPSOLVER_API_KEY
        if not self.api_key:
            raise ValueError(
                "CAPSOLVER_API_KEY not set. Sign up at https://www.capsolver.com/"
            )

    async def solve_funcaptcha(self, public_key: str, page_url: str, blob: str = "") -> str | None:
        """
        Solve TikTok's FunCaptcha (Arkose Labs).
        Returns the solution token or None on failure.
        """
        task_payload = {
            "clientKey": self.api_key,
            "task": {
                "type": "FunCaptchaTaskProxyLess",
                "websiteURL": page_url,
                "websitePublicKey": public_key,
            },
        }
        if blob:
            task_payload["task"]["data"] = '{"blob":"' + blob + '"}'

        async with httpx.AsyncClient(timeout=30) as client:
            # Create task
            resp = await client.post(f"{self.BASE_URL}/createTask", json=task_payload)
            result = resp.json()

            if result.get("errorId", 1) != 0:
                log.error("CAPTCHA create error: %s", result.get("errorDescription", "unknown"))
                return None

            task_id = result["taskId"]
            log.info("CAPTCHA task created: %s", task_id)

            # Poll for result
            for _ in range(Config.CAPTCHA_SOLVE_TIMEOUT // 3):
                await asyncio.sleep(3)
                resp = await client.post(
                    f"{self.BASE_URL}/getTaskResult",
                    json={"clientKey": self.api_key, "taskId": task_id},
                )
                result = resp.json()
                status = result.get("status", "")

                if status == "ready":
                    token = result.get("solution", {}).get("token", "")
                    log.info("CAPTCHA solved!")
                    return token
                elif status == "failed":
                    log.error("CAPTCHA failed: %s", result.get("errorDescription", "unknown"))
                    return None

            log.warning("CAPTCHA solve timeout")
            return None

    async def solve_slider_captcha(self, page) -> bool:
        """
        Attempt to solve TikTok's slider/puzzle CAPTCHA via browser interaction.
        This is a fallback that tries to detect and drag the slider piece.
        Returns True if solved, False otherwise.
        """
        try:
            # Wait for puzzle CAPTCHA to appear
            puzzle = await page.wait_for_selector(
                'div[class*="captcha"], #captcha-verify-image', timeout=5000
            )
            if not puzzle:
                return False

            # Look for the slider handle
            slider = await page.query_selector(
                'div[class*="slider--handle"], div[class*="secsdk-captcha-drag-icon"]'
            )
            if not slider:
                log.warning("No slider handle found")
                return False

            # Get slider position
            box = await slider.bounding_box()
            if not box:
                return False

            # Drag the slider across — this is a basic attempt
            start_x = box["x"] + box["width"] / 2
            start_y = box["y"] + box["height"] / 2

            await page.mouse.move(start_x, start_y)
            await page.mouse.down()
            # Move in steps to simulate human behavior
            for i in range(1, 20):
                await page.mouse.move(start_x + i * 15, start_y + (i % 3 - 1))
                await asyncio.sleep(0.05)
            await page.mouse.up()
            await asyncio.sleep(2)

            # Check if CAPTCHA disappeared
            remaining = await page.query_selector(
                'div[class*="captcha"], #captcha-verify-image'
            )
            return remaining is None

        except Exception as e:
            log.error("Slider CAPTCHA error: %s", e)
            return False
