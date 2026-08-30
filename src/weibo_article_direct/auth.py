from __future__ import annotations

import asyncio
import re
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from playwright.async_api import Browser, async_playwright
from playwright.async_api import Error as PlaywrightError

LOGIN_URL = "https://weibo.com/login.php"
MOBILE_CONFIG_URL = "https://m.weibo.cn/api/config"


@dataclass(frozen=True, slots=True)
class OwnerLogin:
    uid: str
    cookies: dict[str, str]
    user_agent: str


async def login_with_qr(*, timeout_seconds: int = 180) -> OwnerLogin:
    """Open the normal login page and retain its session only for this process."""

    playwright = await async_playwright().start()
    browser: Browser | None = None
    try:
        browser = await _launch_browser(playwright)
        context = await browser.new_context(viewport={"width": 1280, "height": 820})
        page = await context.new_page()
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=20_000)
        print("请在打开的微博官方页面完成扫码登录；完成后 CLI 会自动继续。")
        for _ in range(timeout_seconds):
            raw_cookies = await context.cookies([LOGIN_URL, MOBILE_CONFIG_URL])
            cookie_map = {
                str(item["name"]): str(item["value"])
                for item in raw_cookies
                if item.get("name") and item.get("value")
            }
            uid = _uid_from_login_cookie(cookie_map.get("SUB", ""))
            if uid is None:
                uid = await _uid_from_config(context)
            if uid and cookie_map:
                return OwnerLogin(
                    uid=uid,
                    cookies=cookie_map,
                    user_agent=await page.evaluate("navigator.userAgent"),
                )
            await asyncio.sleep(1)
        raise TimeoutError("未在限定时间内完成扫码登录。")
    finally:
        if browser is not None:
            with suppress(PlaywrightError):
                await browser.close()
        with suppress(PlaywrightError):
            await playwright.stop()


async def _launch_browser(playwright: Any) -> Browser:
    failures: list[str] = []
    for channel in ("msedge", "chrome", None):
        try:
            return await playwright.chromium.launch(headless=False, channel=channel)
        except PlaywrightError as exc:
            failures.append(type(exc).__name__)
    raise RuntimeError(
        "未找到可用浏览器。请安装 Microsoft Edge/Chrome，或运行 playwright install chromium。"
        f" ({', '.join(failures)})"
    )


def _uid_from_login_cookie(value: str) -> str | None:
    match = re.search(r"_T-(\d+)-", value)
    return match.group(1) if match else None


async def _uid_from_config(context: Any) -> str | None:
    try:
        response = await context.request.get(MOBILE_CONFIG_URL, timeout=5_000)
        return _find_uid(await response.json())
    except (PlaywrightError, ValueError, TypeError, AttributeError):
        return None


def _find_uid(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("uid", "uidstr", "user_id"):
            candidate = str(value.get(key) or "")
            if candidate.isdigit():
                return candidate
        for nested in value.values():
            found = _find_uid(nested)
            if found:
                return found
    if isinstance(value, list):
        for nested in value:
            found = _find_uid(nested)
            if found:
                return found
    return None
