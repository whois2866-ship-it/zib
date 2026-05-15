#!/usr/bin/env python3
"""
TikTok Account Creator — CLI entry point.

Usage:
    python create_accounts.py --count 5
    python create_accounts.py --count 3 --emails emails.txt
    python create_accounts.py --count 1 --email custom@mail.botwave.online
    python create_accounts.py --count 10 --concurrent 3 --headless
"""

import argparse
import asyncio
import csv
import os
import sys

from playwright.async_api import async_playwright

from config import Config
from captcha_solver import CaptchaSolver
from email_handler import PostalEmailHandler, EmailListHandler
from proxy_manager import ProxyManager
from signup_flow import create_account, random_email
from stealth import random_profile, apply_stealth
from logger import log


def save_account(account: dict):
    """Append account to CSV file."""
    file_exists = os.path.exists(Config.ACCOUNTS_FILE)
    with open(Config.ACCOUNTS_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["email", "password", "username", "status"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(account)


async def create_single_account(
    playwright_instance,
    proxy_manager: ProxyManager,
    captcha_solver: CaptchaSolver,
    postal: PostalEmailHandler,
    email_addr: str,
    account_num: int,
    total: int,
    headless: bool = False,
) -> dict | None:
    """Create a single account with retry logic."""
    for attempt in range(1, Config.MAX_RETRIES + 1):
        log.info("--- Account %d of %d (attempt %d/%d) ---",
                 account_num, total, attempt, Config.MAX_RETRIES)

        proxy = proxy_manager.next()
        profile = random_profile()

        launch_args = {
            "headless": headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
            ],
        }
        if proxy:
            launch_args["proxy"] = proxy
            log.info("Using proxy: %s", proxy["server"])

        browser = await playwright_instance.chromium.launch(**launch_args)

        context = await browser.new_context(
            viewport=profile["viewport"],
            screen=profile["screen"],
            user_agent=profile["user_agent"],
            locale=profile["locale"],
            timezone_id=profile["timezone_id"],
            color_scheme=profile["color_scheme"],
            device_scale_factor=profile["device_scale_factor"],
        )

        await apply_stealth(context, profile)

        # Use a fresh email on retry
        retry_email = email_addr if attempt == 1 else random_email()

        result = await create_account(
            context=context,
            proxy_manager=proxy_manager,
            captcha_solver=captcha_solver,
            postal=postal,
            email_addr=retry_email,
        )

        await browser.close()

        if result and result["status"] == "success":
            return result

        if attempt < Config.MAX_RETRIES:
            log.warning("Attempt %d failed, retrying in %ds...", attempt, Config.RETRY_DELAY)
            await asyncio.sleep(Config.RETRY_DELAY)

    log.error("All %d attempts failed for account %d", Config.MAX_RETRIES, account_num)
    return None


async def main(
    count: int,
    email_file: str = "",
    single_email: str = "",
    headless: bool = False,
    concurrent: int = 1,
):
    log.info("=" * 60)
    log.info("  TikTok Account Creator")
    log.info("  Creating %d account(s)  |  Concurrency: %d  |  Headless: %s",
             count, concurrent, headless)
    log.info("=" * 60)

    # Initialize components
    try:
        captcha_solver = CaptchaSolver()
    except ValueError as e:
        log.error("%s", e)
        log.error("Set CAPSOLVER_API_KEY in your .env file")
        sys.exit(1)

    postal = PostalEmailHandler()
    proxy_manager = ProxyManager()

    # Load emails if provided
    email_list = None
    if email_file:
        email_list = EmailListHandler(email_file)
        if email_list.remaining() < count:
            log.warning("Only %d emails available, need %d", email_list.remaining(), count)
            count = email_list.remaining()

    # Build list of emails
    emails: list[str] = []
    for i in range(count):
        if single_email and i == 0:
            emails.append(single_email)
        elif email_list:
            addr = email_list.next_email()
            if addr:
                emails.append(addr)
            else:
                break
        else:
            emails.append(random_email())

    count = len(emails)
    created = 0
    failed = 0

    async with async_playwright() as p:
        if concurrent <= 1:
            # Sequential mode
            for i, email_addr in enumerate(emails):
                result = await create_single_account(
                    p, proxy_manager, captcha_solver, postal,
                    email_addr, i + 1, count, headless,
                )
                if result and result["status"] == "success":
                    save_account(result)
                    created += 1
                else:
                    failed += 1
                    save_account({
                        "email": email_addr,
                        "password": Config.DEFAULT_PASSWORD,
                        "username": "",
                        "status": "failed",
                    })

                # Delay between accounts
                if i < count - 1:
                    delay = 30 + (i * 5)
                    log.info("Waiting %ds before next account...", delay)
                    await asyncio.sleep(delay)
        else:
            # Concurrent mode — process in batches
            semaphore = asyncio.Semaphore(concurrent)

            async def bounded_create(idx: int, email_addr: str):
                async with semaphore:
                    return idx, email_addr, await create_single_account(
                        p, proxy_manager, captcha_solver, postal,
                        email_addr, idx + 1, count, headless,
                    )

            tasks = [bounded_create(i, em) for i, em in enumerate(emails)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for item in results:
                if isinstance(item, Exception):
                    log.error("Task exception: %s", item)
                    failed += 1
                    continue
                idx, email_addr, result = item
                if result and result["status"] == "success":
                    save_account(result)
                    created += 1
                else:
                    failed += 1
                    save_account({
                        "email": email_addr,
                        "password": Config.DEFAULT_PASSWORD,
                        "username": "",
                        "status": "failed",
                    })

    # Final report
    log.info("=" * 60)
    log.info("  RESULTS")
    log.info("  Created: %d", created)
    log.info("  Failed:  %d", failed)
    log.info("  Total:   %d", count)
    log.info("  Accounts saved to: %s", Config.ACCOUNTS_FILE)
    log.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TikTok Account Creator")
    parser.add_argument("--count", type=int, default=1, help="Number of accounts to create")
    parser.add_argument("--emails", type=str, default="", help="Path to file with email list")
    parser.add_argument("--email", type=str, default="", help="Single email to use")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--concurrent", type=int, default=1,
                        help="Number of accounts to create concurrently (default: 1)")
    args = parser.parse_args()

    asyncio.run(main(
        count=args.count,
        email_file=args.emails,
        single_email=args.email,
        headless=args.headless,
        concurrent=args.concurrent,
    ))
