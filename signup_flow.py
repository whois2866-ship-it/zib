"""
TikTok signup flow using Playwright.
Handles the full account creation process:
1. Navigate to signup page
2. Fill in birthday
3. Enter email and password
4. Solve CAPTCHA
5. Enter verification code from Postal
6. Complete signup
"""

import asyncio
import random
import string

from playwright.async_api import async_playwright, Page, BrowserContext

from config import Config
from captcha_solver import CaptchaSolver
from email_handler import PostalEmailHandler
from proxy_manager import ProxyManager
from logger import log


def random_string(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def random_email() -> str:
    prefix = random_string(10)
    return f"{prefix}@mail.botwave.online"


async def human_type(page: Page, selector: str, text: str):
    """Type text with random delays to mimic human behavior."""
    await page.click(selector)
    for char in text:
        await page.keyboard.type(char, delay=random.randint(50, 150))
    await asyncio.sleep(random.uniform(0.3, 0.8))


async def random_delay(min_s: float = 0.5, max_s: float = 2.0):
    await asyncio.sleep(random.uniform(min_s, max_s))


async def select_birthday(page: Page):
    """Select birthday from dropdowns on TikTok signup page."""
    month = Config.BIRTH_MONTH
    day = Config.BIRTH_DAY
    year = Config.BIRTH_YEAR

    # Click Month dropdown
    try:
        month_select = page.locator('select[aria-label="Month"]').first
        if await month_select.count() > 0:
            await month_select.select_option(value=str(month))
            await random_delay(0.3, 0.8)

        day_select = page.locator('select[aria-label="Day"]').first
        if await day_select.count() > 0:
            await day_select.select_option(value=str(day))
            await random_delay(0.3, 0.8)

        year_select = page.locator('select[aria-label="Year"]').first
        if await year_select.count() > 0:
            await year_select.select_option(value=str(year))
            await random_delay(0.3, 0.8)

        log.info("Birthday set: %d/%d/%d", month, day, year)
        return True
    except Exception:
        pass

    # Fallback: try clicking date containers
    try:
        month_containers = page.locator('[data-e2e="month-container"], [class*="month"]')
        if await month_containers.count() > 0:
            await month_containers.first.click()
            await random_delay()
            month_option = page.locator(f'text="{month}"').first
            if await month_option.count() > 0:
                await month_option.click()
                await random_delay()

        day_containers = page.locator('[data-e2e="day-container"], [class*="day"]')
        if await day_containers.count() > 0:
            await day_containers.first.click()
            await random_delay()
            day_option = page.locator(f'text="{day}"').first
            if await day_option.count() > 0:
                await day_option.click()
                await random_delay()

        year_containers = page.locator('[data-e2e="year-container"], [class*="year"]')
        if await year_containers.count() > 0:
            await year_containers.first.click()
            await random_delay()
            year_option = page.locator(f'text="{year}"').first
            if await year_option.count() > 0:
                await year_option.click()
                await random_delay()

        log.info("Birthday set (fallback): %d/%d/%d", month, day, year)
        return True
    except Exception as e:
        log.warning("Birthday selection failed: %s", e)
        return False


async def fill_email_and_password(page: Page, email_addr: str, password: str):
    """Fill in email and password fields."""
    # Try various selectors for email input
    email_selectors = [
        'input[name="email"]',
        'input[type="email"]',
        'input[placeholder*="email" i]',
        'input[data-e2e="email-input"]',
    ]
    for sel in email_selectors:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                await human_type(page, sel, email_addr)
                log.info("Email entered: %s", email_addr)
                break
        except Exception:
            continue

    await random_delay(0.5, 1.0)

    # Password
    password_selectors = [
        'input[name="password"]',
        'input[type="password"]',
        'input[placeholder*="password" i]',
        'input[data-e2e="password-input"]',
    ]
    for sel in password_selectors:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                await human_type(page, sel, password)
                log.info("Password entered")
                break
        except Exception:
            continue


async def handle_captcha(page: Page, solver: CaptchaSolver) -> bool:
    """Detect and solve CAPTCHA if present."""
    await asyncio.sleep(2)

    # Check for FunCaptcha iframe
    funcaptcha_frame = page.frame_locator('iframe[src*="funcaptcha"], iframe[src*="arkoselabs"]')
    try:
        fc_element = funcaptcha_frame.locator("body").first
        if await fc_element.count() > 0:
            log.info("FunCaptcha detected, solving via API...")
            # Extract public key from iframe src
            frames = page.frames
            public_key = ""
            for frame in frames:
                if "funcaptcha" in frame.url or "arkoselabs" in frame.url:
                    import re
                    match = re.search(r"pk=([^&]+)", frame.url)
                    if match:
                        public_key = match.group(1)
                    break

            if public_key:
                token = await solver.solve_funcaptcha(public_key, page.url)
                if token:
                    # Inject the token
                    await page.evaluate(
                        f'document.querySelector("[name=fc-token]").value = "{token}";'
                    )
                    return True
    except Exception:
        pass

    # Check for slider/puzzle captcha
    slider_present = await page.query_selector(
        'div[class*="captcha"], #captcha-verify-image, [class*="secsdk"]'
    )
    if slider_present:
        log.info("Slider CAPTCHA detected, attempting to solve...")
        return await solver.solve_slider_captcha(page)

    log.info("No CAPTCHA detected")
    return True


async def submit_and_verify(page: Page, email_addr: str, postal: PostalEmailHandler) -> bool:
    """Click submit/next and handle email verification."""
    # Click the submit/signup/next button
    submit_selectors = [
        'button[data-e2e="signup-button"]',
        'button[type="submit"]',
        'button:has-text("Next")',
        'button:has-text("Sign up")',
        'button:has-text("Register")',
    ]
    for sel in submit_selectors:
        try:
            btn = page.locator(sel).first
            if await btn.count() > 0 and await btn.is_visible():
                await btn.click()
                log.info("Submit clicked")
                break
        except Exception:
            continue

    await asyncio.sleep(3)

    # Check if verification code input appeared
    code_selectors = [
        'input[data-e2e="code-input"]',
        'input[placeholder*="code" i]',
        'input[placeholder*="verification" i]',
        'input[name="code"]',
    ]

    code_input = None
    for sel in code_selectors:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                code_input = sel
                break
        except Exception:
            continue

    if not code_input:
        log.warning("No verification code input found")
        return False

    # Sometimes need to click "Send code" button first
    send_code_btn = page.locator(
        'button:has-text("Send code"), a:has-text("Send code"), '
        'button:has-text("Send"), [data-e2e="send-code-button"]'
    ).first
    if await send_code_btn.count() > 0:
        await send_code_btn.click()
        log.info("Sent verification code request")
        await asyncio.sleep(2)

    # Wait for verification code from Postal
    log.info("Waiting for verification code via Postal...")
    code = await postal.get_messages(email_addr, timeout=120, poll_interval=5)
    if not code:
        log.error("Failed to get verification code!")
        return False

    # Enter the code
    await human_type(page, code_input, code)
    await random_delay(0.5, 1.0)

    # Click verify/next
    verify_selectors = [
        'button:has-text("Next")',
        'button:has-text("Verify")',
        'button:has-text("Submit")',
        'button[type="submit"]',
    ]
    for sel in verify_selectors:
        try:
            btn = page.locator(sel).first
            if await btn.count() > 0 and await btn.is_visible():
                await btn.click()
                break
        except Exception:
            continue

    await asyncio.sleep(3)
    return True


async def check_signup_success(page: Page) -> bool:
    """Check if signup was successful by looking for success indicators."""
    # Check URL changed to feed or profile
    url = page.url.lower()
    if "/foryou" in url or "/feed" in url or "/@" in url:
        return True

    # Check for username creation page (means signup succeeded)
    username_input = page.locator(
        'input[data-e2e="username-input"], input[placeholder*="username" i]'
    ).first
    if await username_input.count() > 0:
        return True

    # Check for common error messages
    error = page.locator(
        '[class*="error"], [data-e2e="signup-error"], [class*="ErrorMessage"]'
    ).first
    if await error.count() > 0:
        error_text = await error.inner_text()
        log.error("Signup error: %s", error_text)
        return False

    return False


async def set_username(page: Page, username: str = "") -> str:
    """Set username if prompted after signup."""
    if not username:
        username = "user_" + random_string(8)

    try:
        input_el = page.locator(
            'input[data-e2e="username-input"], input[placeholder*="username" i]'
        ).first
        if await input_el.count() > 0:
            await input_el.fill("")
            await human_type(page, 'input[data-e2e="username-input"], input[placeholder*="username" i]', username)

            # Click save/confirm
            save_btn = page.locator(
                'button:has-text("Sign up"), button:has-text("Save"), button[type="submit"]'
            ).first
            if await save_btn.count() > 0:
                await save_btn.click()
                await asyncio.sleep(2)
            log.info("Username set: %s", username)
    except Exception as e:
        log.warning("Username setting failed: %s", e)

    return username


async def create_account(
    context: BrowserContext,
    proxy_manager: ProxyManager,
    captcha_solver: CaptchaSolver,
    postal: PostalEmailHandler,
    email_addr: str = "",
    password: str = "",
) -> dict | None:
    """
    Full account creation flow.
    Returns dict with account details or None on failure.
    """
    if not email_addr:
        email_addr = random_email()
    if not password:
        password = Config.DEFAULT_PASSWORD

    page = await context.new_page()
    result = None

    try:
        log.info("=" * 50)
        log.info("Creating account with: %s", email_addr)
        log.info("=" * 50)

        # Navigate to signup
        await page.goto(Config.SIGNUP_URL, timeout=Config.PAGE_LOAD_TIMEOUT)
        await asyncio.sleep(3)
        log.info("Signup page loaded")

        # Step 1: Birthday
        if not await select_birthday(page):
            log.error("Could not set birthday")
            return None

        # Click Next after birthday
        next_btn = page.locator('button:has-text("Next"), button[type="submit"]').first
        if await next_btn.count() > 0:
            await next_btn.click()
            await asyncio.sleep(2)

        # Step 2: Email and password
        await fill_email_and_password(page, email_addr, password)

        # Step 3: Handle CAPTCHA
        captcha_ok = await handle_captcha(page, captcha_solver)
        if not captcha_ok:
            log.error("CAPTCHA not solved")
            return None

        # Step 4: Submit and verify email
        verified = await submit_and_verify(page, email_addr, postal)
        if not verified:
            log.error("Email verification failed")
            return None

        # Step 5: Check success
        await asyncio.sleep(3)
        success = await check_signup_success(page)

        if success:
            username = await set_username(page)
            result = {
                "email": email_addr,
                "password": password,
                "username": username,
                "status": "success",
            }
            log.info("SUCCESS! Account created: %s / %s", email_addr, username)
        else:
            log.error("Signup did not complete successfully")
            # Take a screenshot for debugging
            await page.screenshot(path=f"debug_{random_string(6)}.png")

    except Exception as e:
        log.error("Account creation error: %s", e)

    finally:
        await page.close()

    return result
