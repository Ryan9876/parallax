from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from .browser_evidence import (
    BrowserAdapterError,
    BrowserAdapterResult,
    BrowserAdapterTimeout,
    BrowserAssertion,
    BrowserAssertionKind,
    BrowserPolicyDenied,
)


_ALLOWED_ROLES = frozenset(
    {
        "alert",
        "button",
        "checkbox",
        "dialog",
        "heading",
        "link",
        "list",
        "listitem",
        "main",
        "navigation",
        "radio",
        "region",
        "status",
        "tab",
        "tabpanel",
        "textbox",
    }
)


def _origin(url: str) -> tuple[str, str, int]:
    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port or (443 if scheme == "https" else 80)
    return scheme, host, port


class SyncPlaywrightBrowserAdapter:
    """Concrete read-only Playwright adapter for the S4 browser evidence contract.

    The adapter deliberately has no generic evaluate, cookie, header, request,
    form-submit, download, upload, or mutation API. A session is locked to the
    exact origin supplied by the first admitted navigation. Every browser
    request outside that origin is aborted before transport.
    """

    def __init__(self, *, headless: bool = True, viewport_width: int = 1440, viewport_height: int = 900):
        if not isinstance(headless, bool):
            raise TypeError("headless must be bool")
        for name, value in (("viewport_width", viewport_width), ("viewport_height", viewport_height)):
            if not isinstance(value, int) or isinstance(value, bool) or not 320 <= value <= 4_096:
                raise ValueError(f"{name} is outside the protected browser viewport bound")
        self._headless = headless
        self._viewport = {"width": viewport_width, "height": viewport_height}
        self._playwright: Any | None = None
        self._browser: Any | None = None
        self._context: Any | None = None
        self._page: Any | None = None
        self._timeout_error: type[BaseException] | tuple[type[BaseException], ...] = TimeoutError
        self._admitted_origin: tuple[str, str, int] | None = None
        self._policy_violation = False
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def _start(self, admitted_url: str) -> None:
        if self._closed:
            raise BrowserAdapterError("Playwright browser adapter is closed")
        if self._page is not None:
            if _origin(admitted_url) != self._admitted_origin:
                raise BrowserPolicyDenied("browser session cannot widen its admitted origin")
            return
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserAdapterError(
                "Playwright runtime is unavailable; install the browser worker dependency and Chromium runtime"
            ) from exc

        self._timeout_error = (TimeoutError, PlaywrightTimeoutError)
        self._admitted_origin = _origin(admitted_url)
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self._headless)
            self._context = self._browser.new_context(viewport=self._viewport)
            self._context.route("**/*", self._route_request)
            self._page = self._context.new_page()
        except Exception as exc:
            self.close()
            raise BrowserAdapterError("Playwright browser session could not be initialized") from exc

    def _route_request(self, route: Any, request: Any) -> None:
        try:
            target_origin = _origin(str(request.url))
        except Exception:
            self._policy_violation = True
            route.abort()
            return
        if target_origin != self._admitted_origin:
            self._policy_violation = True
            route.abort()
            return
        route.continue_()

    def _require_page(self) -> Any:
        if self._closed:
            raise BrowserAdapterError("Playwright browser adapter is closed")
        if self._page is None:
            raise BrowserAdapterError("admitted navigation must occur before browser inspection")
        return self._page

    def _call(self, fn):
        self._policy_violation = False
        try:
            return fn()
        except self._timeout_error as exc:
            raise BrowserAdapterTimeout("bounded Playwright operation timed out") from exc
        except BrowserPolicyDenied:
            raise
        except Exception as exc:
            if self._policy_violation:
                raise BrowserPolicyDenied("browser request or redirect left the admitted origin") from exc
            raise BrowserAdapterError("bounded Playwright operation failed") from exc

    def navigate(self, url: str, *, timeout_ms: int) -> BrowserAdapterResult:
        self._start(url)
        page = self._require_page()

        def operation():
            response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            if self._policy_violation:
                raise BrowserPolicyDenied("browser request or redirect left the admitted origin")
            if response is not None and int(response.status) >= 500:
                raise BrowserAdapterError("admitted target returned a server error")
            title = str(page.title() or "").strip()
            observations = (f"title: {title[:180]}",) if title else ()
            return BrowserAdapterResult(final_url=str(page.url), observations=observations)

        return self._call(operation)

    def inspect(self, *, timeout_ms: int, max_items: int) -> BrowserAdapterResult:
        page = self._require_page()

        def operation():
            page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
            observations: list[str] = []
            title = str(page.title() or "").strip()
            if title:
                observations.append(f"title: {title[:180]}")
            for selector, label in (("h1,h2,h3", "heading"), ("button", "button"), ("a", "link")):
                if len(observations) >= max_items:
                    break
                texts = page.locator(selector).all_inner_texts()
                for text in texts:
                    candidate = " ".join(str(text).split())
                    if candidate:
                        observations.append(f"{label}: {candidate[:180]}")
                    if len(observations) >= max_items:
                        break
            return BrowserAdapterResult(final_url=str(page.url), observations=tuple(observations))

        return self._call(operation)

    def assert_condition(self, assertion: BrowserAssertion, *, timeout_ms: int) -> BrowserAdapterResult:
        page = self._require_page()

        def operation():
            if assertion.kind is BrowserAssertionKind.TEXT_PRESENT:
                passed = page.get_by_text(assertion.expected, exact=True).count() > 0
            elif assertion.kind is BrowserAssertionKind.ROLE_PRESENT:
                role = assertion.expected.strip().lower()
                if role not in _ALLOWED_ROLES:
                    raise BrowserPolicyDenied("requested accessibility role is outside the assertion allowlist")
                passed = page.get_by_role(role).count() > 0
            elif assertion.kind is BrowserAssertionKind.URL_EQUALS:
                passed = str(page.url) == assertion.expected
            else:  # pragma: no cover - BrowserAssertion construction prevents this
                raise BrowserPolicyDenied("assertion kind is outside the allowlist")
            page.wait_for_timeout(min(timeout_ms, 25))
            return BrowserAdapterResult(final_url=str(page.url), assertion_passed=bool(passed))

        return self._call(operation)

    def screenshot(self, *, timeout_ms: int) -> BrowserAdapterResult:
        page = self._require_page()

        def operation():
            page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
            raw = page.screenshot(type="png", full_page=False, animations="disabled")
            viewport = page.viewport_size or self._viewport
            return BrowserAdapterResult(
                final_url=str(page.url),
                screenshot_bytes=bytes(raw),
                viewport_width=int(viewport["width"]),
                viewport_height=int(viewport["height"]),
            )

        return self._call(operation)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for item in (self._context, self._browser, self._playwright):
            if item is None:
                continue
            try:
                if item is self._playwright:
                    item.stop()
                else:
                    item.close()
            except Exception:
                pass
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None


__all__ = ["SyncPlaywrightBrowserAdapter"]
