#!/usr/bin/env python3
"""TikTok mass unfollow script using Playwright CDP."""
 
import asyncio
import time
import sys
 
from playwright.async_api import async_playwright
 
CDP_URL = "http://localhost:29229"
TARGET_FOLLOWING = 20
UNFOLLOW_DELAY = 0.3  # seconds between unfollows
BATCH_SIZE = 50  # unfollows before a longer pause
BATCH_PAUSE = 3  # seconds to pause between batches
REST_EVERY = 200  # rest after this many unfollows
REST_DURATION = 300  # 5 minutes rest
SCROLL_PAUSE = 1  # seconds after scrolling
 
total_unfollowed = 0
errors = 0
 
 
async def get_following_count(page):
    """Get current following count from the profile page or modal."""
    try:
        el = await page.query_selector('strong[title="Following"]')
        if el:
            text = await el.inner_text()
            return int(text.replace(",", ""))
    except Exception:
        pass
    return None
 
 
async def unfollow_batch(page):
    """Find and click 'Following' buttons in the visible list."""
    global total_unfollowed, errors
 
    # Find all buttons that say "Following" or "Friends" (not just "Follow")
    buttons = await page.query_selector_all('button')
    following_buttons = []
    for btn in buttons:
        try:
            label = await btn.get_attribute("aria-label")
            text = await btn.inner_text()
            if text.strip() == "Following" and label and label.startswith("Following "):
                following_buttons.append(btn)
            elif text.strip() == "Friends" and label and label.startswith("Friends "):
                following_buttons.append(btn)
        except Exception:
            continue
 
    if not following_buttons:
        return 0
 
    unfollowed_this_batch = 0
    for btn in following_buttons:
        try:
            # Get the name for logging
            label = await btn.get_attribute("aria-label") or "unknown"
            name = label.replace("Following ", "").replace("Friends ", "")
 
            # Click the "Following" or "Friends" button to unfollow
            await btn.click()
            await asyncio.sleep(0.3)
 
            # Check if a confirmation dialog appeared (Unfollow button)
            try:
                confirm = await page.wait_for_selector(
                    'button:has-text("Unfollow")', timeout=1500
                )
                if confirm:
                    await confirm.click()
                    await asyncio.sleep(0.3)
            except Exception:
                pass
 
            total_unfollowed += 1
            unfollowed_this_batch += 1
            print(f"[{total_unfollowed}] Unfollowed: {name}", flush=True)
 
            # Check target every 50 unfollows
            if total_unfollowed % 50 == 0:
                count = await get_following_count(page)
                if count and count <= TARGET_FOLLOWING:
                    print(f"\nReached target! Following count: {count}", flush=True)
                    return -1
 
            # 5-minute rest every 200 unfollows
            if total_unfollowed % REST_EVERY == 0:
                print(f"\n=== Resting for 5 minutes after {total_unfollowed} unfollows... ===", flush=True)
                await asyncio.sleep(REST_DURATION)
                print(f"=== Rest complete, resuming... ===", flush=True)
            # Delay between unfollows
            elif unfollowed_this_batch % BATCH_SIZE == 0:
                print(f"  Pausing {BATCH_PAUSE}s after {BATCH_SIZE} unfollows...", flush=True)
                await asyncio.sleep(BATCH_PAUSE)
            else:
                await asyncio.sleep(UNFOLLOW_DELAY)
 
        except Exception as e:
            errors += 1
            print(f"  Error unfollowing: {e}", flush=True)
            if errors > 20:
                print("Too many errors, stopping.", flush=True)
                return -2
            await asyncio.sleep(3)
 
    return unfollowed_this_batch
 
 
async def scroll_list(page):
    """Scroll the following list modal to load more accounts."""
    try:
        # Find the scrollable container in the modal
        modal = await page.query_selector('section[aria-modal="true"] div[data-e2e="scroll-container"], section[aria-modal="true"] [class*="scroll"]')
        if modal:
            await modal.evaluate("el => el.scrollTop = el.scrollHeight")
        else:
            # Try scrolling any scrollable div inside the modal
            await page.evaluate("""
                const modal = document.querySelector('section[aria-modal="true"]');
                if (modal) {
                    const scrollable = modal.querySelector('[class*="scroll"]') ||
                                       Array.from(modal.querySelectorAll('div')).find(
                                           d => d.scrollHeight > d.clientHeight && d.clientHeight > 100
                                       );
                    if (scrollable) scrollable.scrollTop = scrollable.scrollHeight;
                }
            """)
        await asyncio.sleep(SCROLL_PAUSE)
    except Exception as e:
        print(f"  Scroll error: {e}", flush=True)
 
 
async def ensure_following_modal_open(page):
    """Make sure the Following list modal is open."""
    modal = await page.query_selector('section[aria-modal="true"]')
    if not modal:
        # Click on the Following count to open the modal
        following_link = await page.query_selector('strong[title="Following"]')
        if following_link:
            parent = await following_link.evaluate_handle("el => el.closest('a') || el.closest('div')")
            await parent.as_element().click()
            await asyncio.sleep(2)
    return await page.query_selector('section[aria-modal="true"]') is not None
 
 
async def main():
    global total_unfollowed
 
    print(f"Starting TikTok unfollow automation...", flush=True)
    print(f"Target: reduce following to {TARGET_FOLLOWING}", flush=True)
 
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0]
        page = context.pages[0]
 
        # Make sure we're on the right page
        url = page.url
        if "tiktok.com/@mototrades11" not in url:
            await page.goto("https://www.tiktok.com/@mototrades11?lang=en")
            await asyncio.sleep(3)
 
        # Get initial following count
        initial_count = await get_following_count(page)
        if initial_count:
            print(f"Current following count: {initial_count}", flush=True)
            needed = initial_count - TARGET_FOLLOWING
            print(f"Need to unfollow: {needed} accounts", flush=True)
        else:
            print("Could not read following count, proceeding anyway...", flush=True)
 
        # Make sure the Following modal is open
        if not await ensure_following_modal_open(page):
            print("ERROR: Could not open Following modal!", flush=True)
            return
 
        print("Following modal is open. Starting unfollow process...", flush=True)
 
        consecutive_empty = 0
        while True:
            result = await unfollow_batch(page)
 
            if result == -1:  # Target reached
                break
            elif result == -2:  # Too many errors
                break
            elif result == 0:
                consecutive_empty += 1
                if consecutive_empty >= 5:
                    # Check if we need to reload
                    count = await get_following_count(page)
                    if count and count <= TARGET_FOLLOWING:
                        print(f"Target reached! Following: {count}", flush=True)
                        break
                    print("No more Following buttons found, scrolling...", flush=True)
                    await scroll_list(page)
                    consecutive_empty = 0
 
                    # If still no buttons after multiple scrolls, try reopening modal
                    result2 = await unfollow_batch(page)
                    if result2 == 0:
                        print("Still no buttons. Closing and reopening modal...", flush=True)
                        # Close modal
                        close_btn = await page.query_selector('[aria-label="Close_button"]')
                        if close_btn:
                            await close_btn.click()
                            await asyncio.sleep(2)
                        # Reopen
                        await ensure_following_modal_open(page)
                        await asyncio.sleep(2)
                        consecutive_empty = 0
            else:
                consecutive_empty = 0
                # Scroll to load more
                await scroll_list(page)
 
            # Progress update every 100 unfollows
            if total_unfollowed > 0 and total_unfollowed % 100 == 0:
                count = await get_following_count(page)
                print(f"\n--- Progress: Unfollowed {total_unfollowed} total. Current following: {count or 'unknown'} ---\n", flush=True)
 
        # Final summary
        final_count = await get_following_count(page)
        print(f"\n{'='*50}", flush=True)
        print(f"DONE! Total unfollowed: {total_unfollowed}", flush=True)
        print(f"Final following count: {final_count or 'unknown'}", flush=True)
        print(f"Errors encountered: {errors}", flush=True)
        print(f"{'='*50}", flush=True)
 
 
if __name__ == "__main__":
    asyncio.run(main())
