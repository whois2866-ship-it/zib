#!/usr/bin/env python3
"""
TikTok Account Creator — CLI entry point.
 
Usage:
    python create_accounts.py --count 5
    python create_accounts.py --count 3 --emails emails.txt
    python create_accounts.py --count 1 --email custom@mail.botwave.online
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
 
 
def save_account(account: dict):
    """Append account to CSV file."""
    file_exists = os.path.exists(Config.ACCOUNTS_FILE)
    with open(Config.ACCOUNTS_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["email", "password", "username", "status"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(account)
 
 
async def main(count: int, email_file: str = "", single_email: str = ""):
    print("=" * 60)
    print("  TikTok Account Creator")
    print(f"  Creating {count} account(s)")
    print("=" * 60)
 
    # Initialize components
    try:
        captcha_solver = CaptchaSolver()
    except ValueError as e:
        print(f"\nERROR: {e}")
        print("Set CAPSOLVER_API_KEY in your .env file")
        sys.exit(1)
 
    postal = PostalEmailHandler()
    proxy_manager = ProxyManager()
 
    # Load emails if provided
    email_list = None
    if email_file:
        email_list = EmailListHandler(email_file)
        if email_list.remaining() < count:
            print(f"\nWARNING: Only {email_list.remaining()} emails available, need {count}")
            count = email_list.remaining()
 
    # Stats
    created = 0
    failed = 0
 
    async with async_playwright() as p:
        for i in range(count):
            print(f"\n--- Account {i + 1} of {count} ---")
 
            # Get proxy for this account
            proxy = proxy_manager.next()
 
            # Launch browser with proxy
            launch_args = {
                "headless": False,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            }
            if proxy:
                launch_args["proxy"] = proxy
                print(f"  Using proxy: {proxy['server']}")
 
            browser = await p.chromium.launch(**launch_args)
 
            # Create context with realistic settings
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="en-US",
                timezone_id="America/New_York",
            )
 
            # Stealth: remove webdriver flag
            await context.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
                """
            )
 
            # Get email for this account
            if single_email and i == 0:
                email_addr = single_email
            elif email_list:
                email_addr = email_list.next_email()
                if not email_addr:
                    print("  No more emails available!")
                    break
            else:
                email_addr = random_email()
 
            # Create account
            result = await create_account(
                context=context,
                proxy_manager=proxy_manager,
                captcha_solver=captcha_solver,
                postal=postal,
                email_addr=email_addr,
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
 
            await browser.close()
 
            # Delay between accounts
            if i < count - 1:
                delay = 30 + (i * 5)  # Increasing delay
                print(f"\n  Waiting {delay}s before next account...")
                await asyncio.sleep(delay)
 
    # Final report
    print("\n" + "=" * 60)
    print(f"  RESULTS")
    print(f"  Created: {created}")
    print(f"  Failed:  {failed}")
    print(f"  Total:   {count}")
    print(f"  Accounts saved to: {Config.ACCOUNTS_FILE}")
    print("=" * 60)
 
 
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TikTok Account Creator")
    parser.add_argument("--count", type=int, default=1, help="Number of accounts to create")
    parser.add_argument("--emails", type=str, default="", help="Path to file with email list")
    parser.add_argument("--email", type=str, default="", help="Single email to use")
    args = parser.parse_args()
 
    asyncio.run(main(count=args.count, email_file=args.emails, single_email=args.email))
