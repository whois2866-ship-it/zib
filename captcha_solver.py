"""
CAPTCHA solving module using CapSolver API.
TikTok uses FunCaptcha (Arkose Labs) for signup protection.
"""
 
import asyncio
import httpx
from config import Config
 
 
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
                print(f"  CAPTCHA create error: {result.get('errorDescription', 'unknown')}")
                return None
 
            task_id = result["taskId"]
            print(f"  CAPTCHA task created: {task_id}")
 
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
                    print("  CAPTCHA solved!")
                    return token
                elif status == "failed":
                    print(f"  CAPTCHA failed: {result.get('errorDescription', 'unknown')}")
                    return None
 
            print("  CAPTCHA solve timeout")
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
                print("  No slider handle found")
                return False
 
            # Get slider position
            box = await slider.bounding_box()
            if not box:
                return False
 
            # Drag the slider across — this is a basic attempt
            # Real CAPTCHA solving would need image analysis
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
            print(f"  Slider CAPTCHA error: {e}")
            return False

config.py
tiktok-account-creator

+40
Added
import os
from dotenv import load_dotenv
 
load_dotenv()
 
 
class Config:
    # CAPTCHA
    CAPSOLVER_API_KEY = os.getenv("CAPSOLVER_API_KEY", "")
 
    # Postal (self-hosted email server)
    POSTAL_URL = os.getenv("POSTAL_URL", "https://postal.botwave.online")
    POSTAL_API_KEY = os.getenv("POSTAL_API_KEY", "")
 
    # Email (IMAP fallback)
    EMAIL_IMAP_SERVER = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
    EMAIL_IMAP_PORT = int(os.getenv("EMAIL_IMAP_PORT", "993"))
    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
 
    # Proxy
    PROXY_URL = os.getenv("PROXY_URL", "")
    ROTATING_PROXY_URL = os.getenv("ROTATING_PROXY_URL", "")
 
    # Account defaults
    DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "TikT0k_Auto!2024")
    BIRTH_YEAR = int(os.getenv("BIRTH_YEAR", "1998"))
    BIRTH_MONTH = int(os.getenv("BIRTH_MONTH", "6"))
    BIRTH_DAY = int(os.getenv("BIRTH_DAY", "15"))
 
    # TikTok
    SIGNUP_URL = "https://www.tiktok.com/signup/phone-or-email/email"
 
    # Timing
    ACTION_DELAY = 1.5  # seconds between actions (human-like)
    PAGE_LOAD_TIMEOUT = 30000  # ms
    CAPTCHA_SOLVE_TIMEOUT = 120  # seconds
 
    # Output
    ACCOUNTS_FILE = "accounts.csv"
