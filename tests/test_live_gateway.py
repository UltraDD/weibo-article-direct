from __future__ import annotations

import asyncio
from pathlib import Path

from weibo_article_direct.live_gateway import HttpResponse, LiveArticleGateway
from weibo_article_direct.models import Article, ArticleBlock
from weibo_article_direct.publisher import ArticlePublisher


class StubHttp:
    def __init__(self, responses: list[HttpResponse]) -> None:
        self._responses = iter(responses)
        self.calls: list[dict[str, object]] = []

    async def request(self, method: str, url: str, **kwargs: object) -> HttpResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        return next(self._responses)


def test_WHEN_creating_a_draft_THEN_runtime_identifiers_are_not_fixed():
    http = StubHttp([HttpResponse(200, {"code": "100000", "data": {"id": "draft-1"}})])
    gateway = LiveArticleGateway(http=http, uid="42")

    response = asyncio.run(gateway.create_draft())

    assert response.code == "100000"
    assert http.calls[0]["method"] == "POST"
    assert str(http.calls[0]["url"]).endswith("/article/v5/aj/editor/draft/create")
    assert http.calls[0]["params"] == {"uid": "42", "_rid": http.calls[0]["params"]["_rid"]}
    assert http.calls[0]["params"]["_rid"]


def test_WHEN_saving_a_draft_THEN_safe_default_form_is_used():
    http = StubHttp([HttpResponse(200, {"code": "100000", "data": {}})])
    gateway = LiveArticleGateway(http=http, uid="42")

    response = asyncio.run(
        gateway.save_draft(
            "draft-1",
            title="Article title",
            content="<p>Body</p>",
            cover="",
            action="1",
            follow_to_read="0",
        )
    )

    assert response.code == "100000"
    form = http.calls[0]["form"]
    assert form["id"] == "draft-1"
    assert form["title"] == "Article title"
    assert form["extra"] == "[]"
    assert form["follow_to_read"] == "0"
    assert form["is_v4"] == "1"
    assert "is_original" not in form


def test_WHEN_platform_returns_numeric_zero_THEN_gateway_normalizes_it_as_success():
    http = StubHttp([HttpResponse(200, {"code": 0, "data": {"id": "draft-1"}})])

    response = asyncio.run(LiveArticleGateway(http=http, uid="42").create_draft())

    assert response.code == "0"


def test_WHEN_upload_is_blocked_THEN_gateway_marks_it_as_a_stop_condition(tmp_path: Path):
    image = tmp_path / "cover.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 32)
    http = StubHttp([HttpResponse(403, {"code": "403"}, "blocked")])
    gateway = LiveArticleGateway(http=http, uid="42")

    response = asyncio.run(gateway.upload_image(str(image)))

    assert response.blocked is True
    assert response.code == "403"
    assert len(http.calls) == 1


def test_WHEN_live_adapter_completes_text_article_THEN_writes_once_and_fresh_reads():
    http = StubHttp(
        [
            HttpResponse(200, {"code": "100000", "data": {"id": "draft-1"}}),
            HttpResponse(200, {"code": "100000", "data": {}}),
            HttpResponse(200, {"code": "100000", "data": {}}),
            HttpResponse(200, {"code": "100000", "data": {}}),
            HttpResponse(200, {"code": "100000", "data": {"is_aigc_used": "0"}}),
            HttpResponse(
                200,
                {
                    "code": "100000",
                    "data": {
                        "object_id": "1022:article-1",
                        "url": "https://weibo.com/ttarticle/p/show?id=article-1",
                    },
                },
            ),
            HttpResponse(200, body_text="<title>Article &amp; title</title>"),
        ]
    )

    result = asyncio.run(
        ArticlePublisher(LiveArticleGateway(http=http, uid="42")).publish(
            Article(title="Article & title", blocks=(ArticleBlock.paragraph("Body"),))
        )
    )

    assert result.accepted and result.verified
    assert [call["method"] for call in http.calls].count("POST") == 5
    assert [call["url"] for call in http.calls][-2].endswith("/article/v5/aj/editor/draft/publish")
    assert http.calls[-1]["url"] == "https://weibo.com/ttarticle/p/show?id=article-1"


def test_WHEN_fresh_read_url_is_not_a_trusted_weibo_url_THEN_gateway_stops_without_network():
    http = StubHttp([])
    gateway = LiveArticleGateway(http=http, uid="42")

    response = asyncio.run(
        gateway.verify_article(
            "article-1",
            "Article title",
            "https://example.invalid/article-1",
        )
    )

    assert response.indeterminate is True
    assert response.code == "unsafe_verify_url"
    assert http.calls == []
