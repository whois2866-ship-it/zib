"""
Account warming module — performs post-signup actions
to make newly created accounts look more legitimate.
"""

import asyncio
import random

from playwright.async_api import Page

from logger import log


async def warm_account(page: Page, username: str = ""):
    """Run a series of warming actions on a newly created account."""
    log.info("Starting account warming for %s...", username or "new account")

    await _scroll_feed(page)
    await _like_random_videos(page, count=random.randint(2, 5))
    await _watch_videos(page, count=random.randint(3, 6))
    await _visit_explore(page)

    log.info("Account warming complete")


async def _scroll_feed(page: Page):
    """Scroll through the For You feed to generate activity."""
    try:
        await page.goto("https://www.tiktok.com/foryou", timeout=15000)
        await asyncio.sleep(3)

        for _ in range(random.randint(3, 7)):
            await page.keyboard.press("ArrowDown")
            await asyncio.sleep(random.uniform(2.0, 5.0))

        log.debug("Feed scrolled")
    except Exception as e:
        log.debug("Feed scroll skipped: %s", e)


async def _like_random_videos(page: Page, count: int = 3):
    """Like a few videos on the feed."""
    liked = 0
    try:
        like_buttons = await page.query_selector_all(
            '[data-e2e="like-icon"], button[aria-label*="like" i]'
        )
        random.shuffle(like_buttons)

        for btn in like_buttons[:count]:
            try:
                await btn.click()
                liked += 1
                await asyncio.sleep(random.uniform(1.0, 3.0))
            except Exception:
                continue

        if liked:
            log.debug("Liked %d videos", liked)
    except Exception as e:
        log.debug("Like skipped: %s", e)


async def _watch_videos(page: Page, count: int = 3):
    """Watch videos for a realistic duration."""
    try:
        for i in range(count):
            watch_time = random.uniform(5.0, 15.0)
            await asyncio.sleep(watch_time)
            await page.keyboard.press("ArrowDown")
            log.debug("Watched video %d for %.1fs", i + 1, watch_time)
    except Exception as e:
        log.debug("Watch skipped: %s", e)


async def _visit_explore(page: Page):
    """Visit the explore/discover page."""
    try:
        await page.goto("https://www.tiktok.com/explore", timeout=15000)
        await asyncio.sleep(random.uniform(3.0, 6.0))

        for _ in range(random.randint(2, 4)):
            await page.keyboard.press("ArrowDown")
            await asyncio.sleep(random.uniform(1.5, 3.0))

        log.debug("Explore page visited")
    except Exception as e:
        log.debug("Explore skipped: %s", e)
