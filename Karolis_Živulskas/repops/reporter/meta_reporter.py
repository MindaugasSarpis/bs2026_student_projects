"""Playwright-driven Meta report submission.

Meta has no public reporting API, so this automates the in-browser flow.
The flow is fragile — Meta updates their UI regularly. Treat as best-effort
and monitor failure rates in Grafana.
"""

from __future__ import annotations

from dataclasses import dataclass

from playwright.async_api import (
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeout,
    async_playwright,
)

from repops.observability.logging import get_logger

_FB_BASE = "https://www.facebook.com"
from repops.settings import settings

logger = get_logger(__name__)

_TIMEOUT = 15_000  # ms

_CATEGORY_SELECTORS: dict[str, list[str]] = {
    "hate_speech": [
        "text=Hate speech",
        "text=Hate Speech",
        '[aria-label="Hate speech"]',
    ],
    "false_information": [
        "text=False information",
        "text=False Information",
        '[aria-label="False information"]',
    ],
    "harassment": [
        "text=Harassment",
        '[aria-label="Harassment"]',
    ],
}


@dataclass
class ReportSubmissionResult:
    success: bool
    reference_id: str | None = None
    error: str | None = None


async def submit_report(
    post_url: str,
    category: str = "hate_speech",
) -> ReportSubmissionResult:
    """Navigate to a post URL and submit a report for the given category.

    Returns a ReportSubmissionResult indicating success or failure.
    """
    async with async_playwright() as playwright:
        return await _do_submit(playwright, post_url, category)


async def _do_submit(
    playwright: Playwright,
    post_url: str,
    category: str,
) -> ReportSubmissionResult:
    import json

    browser = await playwright.chromium.launch(headless=True)
    try:
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )

        if settings.fb_session_cookies:
            try:
                cookies = json.loads(settings.fb_session_cookies)
                await context.add_cookies(cookies)
            except Exception as exc:
                logger.error("session_cookie_load_error", error=str(exc))

        page: Page = await context.new_page()

        # 1. Open post
        logger.info("report_opening_post", url=post_url)
        await page.goto(post_url, timeout=_TIMEOUT, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # 2. Click the "…" / more-options menu on the post
        await _open_options_menu(page)

        # 3. Click "Find support or report"
        await _click_report_option(page)

        # 4. Choose report category
        selectors = _CATEGORY_SELECTORS.get(category, _CATEGORY_SELECTORS["hate_speech"])
        clicked = False
        for selector in selectors:
            try:
                await page.click(selector, timeout=5000)
                clicked = True
                break
            except PlaywrightTimeout:
                continue

        if not clicked:
            return ReportSubmissionResult(
                success=False, error=f"Could not find category selector for {category!r}"
            )

        # 5. Submit
        try:
            await page.click("text=Submit", timeout=_TIMEOUT)
            await page.wait_for_timeout(1500)
        except PlaywrightTimeout:
            await page.click("text=Send", timeout=_TIMEOUT)

        logger.info("report_submitted", url=post_url, category=category)
        return ReportSubmissionResult(success=True)

    except PlaywrightTimeout as exc:
        logger.warning("report_submission_timeout", url=post_url, error=str(exc))
        return ReportSubmissionResult(success=False, error=f"Timeout: {exc}")
    except Exception as exc:
        logger.error("report_submission_error", url=post_url, error=str(exc))
        return ReportSubmissionResult(success=False, error=str(exc))
    finally:
        await browser.close()


async def _open_options_menu(page: Page) -> None:
    """Click the post's ⋯ options button."""
    selectors = [
        '[aria-label="Actions for this post"]',
        '[aria-label="More options"]',
        '[data-testid="post_chevron_button"]',
    ]
    for sel in selectors:
        try:
            await page.click(sel, timeout=5000)
            await page.wait_for_timeout(500)
            return
        except PlaywrightTimeout:
            continue
    raise PlaywrightTimeout("Could not open post options menu")


async def _click_report_option(page: Page) -> None:
    """Click the 'Find support or report' / 'Report post' menu item."""
    selectors = [
        "text=Find support or report",
        "text=Report post",
        "text=Report",
    ]
    for sel in selectors:
        try:
            await page.click(sel, timeout=5000)
            await page.wait_for_timeout(500)
            return
        except PlaywrightTimeout:
            continue
    raise PlaywrightTimeout("Could not find report menu item")
