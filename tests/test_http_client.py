from __future__ import annotations

import asyncio

import pytest

from weibo_article_direct.gateway import DirectTransportUnavailable
from weibo_article_direct.http_client import OwnerHttpClient, _decode_json


class _ResponseContext:
    async def __aenter__(self):
        class Response:
            def __init__(self):
                self.status = 200
                self.headers: dict[str, str] = {}

            async def text(self):
                return "{}"

        return Response()

    async def __aexit__(self, *_args):
        return None


class _RecordingSession:
    closed = False

    def __init__(self):
        self.calls: list[dict[str, object]] = []

    def request(self, method: str, url: str, **kwargs: object):
        self.calls.append({"method": method, "url": url, **kwargs})
        return _ResponseContext()


def test_WHEN_upload_returns_json_with_a_non_json_content_type_THEN_payload_is_still_parsed():
    assert _decode_json('{"code":"A00006"}', "text/plain") == {"code": "A00006"}


def test_WHEN_request_target_is_outside_allowed_weibo_hosts_THEN_it_is_refused_before_network():
    client = OwnerHttpClient({"SUB": "owner-session", "XSRF-TOKEN": "owner-xsrf"})
    session = _RecordingSession()
    client._session = session

    with pytest.raises(DirectTransportUnavailable):
        asyncio.run(client.request("GET", "https://example.invalid/article"))

    assert session.calls == []


def test_WHEN_request_targets_a_trusted_weibo_host_THEN_cookie_and_xsrf_are_sent_per_request():
    client = OwnerHttpClient({"SUB": "owner-session", "XSRF-TOKEN": "owner-xsrf"})
    session = _RecordingSession()
    client._session = session

    asyncio.run(client.request("GET", "https://weibo.com/ttarticle/p/show?id=article-1"))

    call = session.calls[0]
    assert call["cookies"] == {"SUB": "owner-session", "XSRF-TOKEN": "owner-xsrf"}
    assert call["headers"]["X-Xsrf-Token"] == "owner-xsrf"
    assert call["allow_redirects"] is False
