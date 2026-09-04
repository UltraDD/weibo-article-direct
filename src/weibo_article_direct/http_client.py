from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Self
from urllib.parse import urlsplit

import aiohttp

from .gateway import DirectTransportUnavailable, DirectWriteIndeterminate

CARD_ORIGIN = "https://card.weibo.com"
HOME_ORIGIN = "https://weibo.com"

_ALLOWED_HOSTS = frozenset(
    {
        "card.weibo.com",
        "picupload.weibo.com",
        "weibo.com",
        "www.weibo.com",
        "m.weibo.cn",
        "weibo.cn",
        "www.weibo.cn",
    }
)


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status: int
    payload: Any = None
    body_text: str = ""


class OwnerHttpClient:
    """In-memory HTTP client for one owner-authorized CLI invocation."""

    def __init__(
        self,
        cookies: Mapping[str, str],
        *,
        user_agent: str = "",
        timeout_seconds: float = 20,
    ) -> None:
        self._cookies = {str(name): str(value) for name, value in cookies.items()}
        self._user_agent = str(user_agent).strip()
        self._timeout_seconds = float(timeout_seconds)
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._cookies.clear()

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        form: Mapping[str, str] | None = None,
        data: bytes | None = None,
        extra_headers: Mapping[str, str] | None = None,
    ) -> HttpResponse:
        if not is_trusted_weibo_url(url):
            raise DirectTransportUnavailable("refusing request to an untrusted host")
        session = await self._ensure_session()
        request_cookies = self._cookies_for_url(url)
        headers = self._request_headers(url, params or {})
        token = request_cookies.get("XSRF-TOKEN") or request_cookies.get("x-xsrf-token")
        if token:
            headers["X-Xsrf-Token"] = token
        headers.update({str(name): str(value) for name, value in (extra_headers or {}).items()})
        try:
            async with session.request(
                method.upper(),
                url,
                params=dict(params or {}) or None,
                data=dict(form or {}) if data is None else data,
                cookies=request_cookies,
                headers=headers,
                allow_redirects=False,
            ) as response:
                raw_text = await response.text()
                # Parse the full body first: draft load/save responses embed the
                # whole article (several KB) and truncating before decoding turns
                # valid success responses into parse failures.
                payload = _decode_json(raw_text, response.headers.get("Content-Type", ""))
                return HttpResponse(
                    response.status, payload=payload, body_text=raw_text[:2000]
                )
        except TimeoutError as exc:
            raise DirectWriteIndeterminate("request timed out after dispatch") from exc
        except aiohttp.ClientError as exc:
            raise DirectTransportUnavailable(type(exc).__name__) from exc

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is not None and not self._session.closed:
            return self._session
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self._timeout_seconds),
            headers={
                "Accept": "application/json, text/plain, */*",
                **({"User-Agent": self._user_agent} if self._user_agent else {}),
            },
        )
        return self._session

    def _cookies_for_url(self, _url: str) -> dict[str, str]:
        """Return the in-memory session for an already trusted Weibo URL."""

        return dict(self._cookies)

    @staticmethod
    def _request_headers(url: str, params: Mapping[str, str]) -> dict[str, str]:
        host = (urlsplit(url).hostname or "").lower()
        if host == "card.weibo.com":
            request_id = str(params.get("_rid") or "")
            return {
                "Origin": CARD_ORIGIN,
                "Referer": f"{CARD_ORIGIN}/article/v5/editor",
                **({"SN-REQID": request_id} if request_id else {}),
            }
        if host == "picupload.weibo.com":
            return {"Origin": CARD_ORIGIN, "Referer": f"{CARD_ORIGIN}/article/v5/editor"}
        if host == "weibo.com" or host.endswith(".weibo.com"):
            return {"Origin": HOME_ORIGIN, "Referer": f"{HOME_ORIGIN}/"}
        return {}


def is_trusted_weibo_url(url: str) -> bool:
    """Return whether a request may carry the owner's session credentials."""

    parsed = urlsplit(str(url))
    try:
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme.lower() == "https"
        and (parsed.hostname or "").lower() in _ALLOWED_HOSTS
        and port in {None, 443}
        and parsed.username is None
        and parsed.password is None
    )


def _decode_json(body_text: str, content_type: str) -> Any:
    if not body_text:
        return None
    if "json" not in content_type.lower() and not body_text.lstrip().startswith(("{", "[")):
        return None
    try:
        return json.loads(body_text)
    except ValueError:
        return None
