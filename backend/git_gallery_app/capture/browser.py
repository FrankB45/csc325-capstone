"""Open a page in headless Chromium and save a screenshot.

Runs inside the capture child process, so this module must NOT import Django.
"""
from urllib.parse import quote, urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from .errors import CaptureError

PAGE_LOAD_TIMEOUT_MS = 30_000    # max wait for the page's "load" event
SETTLE_TIMEOUT_MS = 3_000        # extra best-effort wait for network activity to stop
SCREENSHOT_TIMEOUT_MS = 30_000


def screenshot_page(base_url, page_path, out_path, *, width, height, full_page=True):
    """Load `page_path` from the local server at `base_url` and save a PNG to `out_path`.

    Only requests to `base_url` itself are allowed; everything else is blocked.
    Returns the list of blocked URLs (useful for debugging and for telling users
    why a page may look unstyled).
    Raises CaptureError for problems the user should see.
    """
    page_url = f"{base_url}/{quote(page_path)}"
    allowed_origin = _origin(base_url)
    blocked_urls = []

    def only_allow_local(route):
        # Playwright calls this for EVERY request the page makes: HTML, CSS, JS, images, fetch()...
        if _origin(route.request.url) == allowed_origin:
            route.continue_()
        else:
            blocked_urls.append(route.request.url)
            route.abort()

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except PlaywrightError as error:
            # Not the user's fault; the machine isn't set up. So not a CaptureError.
            raise RuntimeError(
                "Chromium could not start. Did you run 'python -m playwright install chromium'?"
            ) from error

        try:
            context = browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=1,     # 1 CSS pixel = 1 image pixel, on every machine
                service_workers="block",   # service workers could make requests route() can't see
            )
            context.route("**/*", only_allow_local)
            page = context.new_page()

            try:
                response = page.goto(page_url, wait_until="load", timeout=PAGE_LOAD_TIMEOUT_MS)
            except PlaywrightTimeoutError as error:
                raise CaptureError("The page took too long to load.") from error
            if response is None or not response.ok:
                status = response.status if response is not None else "no response"
                raise CaptureError(f"The page could not be opened (HTTP {status}).")

            # Give late requests (images, fetch calls) a moment, but don't fail if
            # the page never goes fully quiet. Some pages poll forever.
            try:
                page.wait_for_load_state("networkidle", timeout=SETTLE_TIMEOUT_MS)
            except PlaywrightTimeoutError:
                pass
            # Wait for web fonts, so text isn't captured in a fallback font.
            page.evaluate("() => document.fonts.ready.then(() => true)")

            try:
                page.screenshot(
                    path=str(out_path),
                    full_page=full_page,
                    animations="disabled",   # finish CSS animations so shots are repeatable
                    timeout=SCREENSHOT_TIMEOUT_MS,
                )
            except PlaywrightTimeoutError as error:
                raise CaptureError("The page took too long to screenshot.") from error

        except PlaywrightError as error:
            # Anything else Playwright raises: the page crashed, the browser died, and so on.
            raise CaptureError("The browser could not render this page.") from error
        finally:
            browser.close()

    return blocked_urls


def _origin(url):
    """("http", "127.0.0.1:54321"): the scheme plus host:port that identify one server."""
    parts = urlsplit(url)
    return (parts.scheme, parts.netloc)