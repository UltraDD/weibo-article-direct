from __future__ import annotations

import asyncio

from weibo_article_direct import (
    Article,
    ArticleBlock,
    ArticlePublisher,
    GatewayResponse,
)


class FakeGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    async def create_draft(self) -> GatewayResponse:
        self.calls.append(("create", None))
        return GatewayResponse(code="100000", data={"id": "draft-1"})

    async def save_draft(self, draft_id: str, **fields: str) -> GatewayResponse:
        self.calls.append(("save", {"id": draft_id, **fields}))
        return GatewayResponse(code="100000")

    async def upload_image(self, path: str) -> GatewayResponse:
        self.calls.append(("upload", path))
        return GatewayResponse(code="100000", data={"url": f"https://img.invalid/{path}"})

    async def attach_image(self, image_url: str) -> GatewayResponse:
        self.calls.append(("attach", image_url))
        return GatewayResponse(code="100000")

    async def load_draft(self, draft_id: str) -> GatewayResponse:
        self.calls.append(("load", draft_id))
        return GatewayResponse(code="100000", data={})

    async def submit_draft(self, draft_id: str, title: str) -> GatewayResponse:
        self.calls.append(("submit", {"id": draft_id, "title": title}))
        return GatewayResponse(
            code="100000", data={"object_id": "1022:article-1", "url": "https://weibo.invalid/article-1"}
        )

    async def verify_article(
        self, remote_id: str, expected_title: str, remote_url: str | None = None
    ) -> GatewayResponse:
        self.calls.append(("verify", {"id": remote_id, "title": expected_title}))
        return GatewayResponse(code="100000")


def test_WHEN_article_has_repeated_body_media_THEN_uploads_once_and_submits_once():
    gateway = FakeGateway()
    publisher = ArticlePublisher(gateway)
    article = Article(
        title="A test article",
        blocks=(
            ArticleBlock.paragraph("Opening"),
            ArticleBlock.image("body.png", caption="Body image"),
            ArticleBlock.image("body.png"),
        ),
        cover_path="cover.png",
    )

    result = asyncio.run(publisher.publish(article))

    assert result.accepted and result.verified
    assert result.remote_id == "article-1"
    assert [name for name, _ in gateway.calls] == [
        "create", "save", "upload", "attach", "save", "upload", "attach", "save", "load", "submit", "verify"
    ]
    assert [value for name, value in gateway.calls if name == "upload"] == ["body.png", "cover.png"]
    submit_calls = [value for name, value in gateway.calls if name == "submit"]
    assert len(submit_calls) == 1


def test_WHEN_a_save_is_rejected_THEN_never_submits():
    class RejectingGateway(FakeGateway):
        async def save_draft(self, draft_id: str, **fields: str) -> GatewayResponse:
            self.calls.append(("save", {"id": draft_id, **fields}))
            return GatewayResponse(code="500002", message="rejected")

    gateway = RejectingGateway()
    result = asyncio.run(
        ArticlePublisher(gateway).publish(
            Article(title="A test article", blocks=(ArticleBlock.paragraph("Body"),))
        )
    )

    assert not result.accepted
    assert result.error_code == "platform_rejected"
    assert "submit" not in [name for name, _ in gateway.calls]


def test_WHEN_submit_response_is_ambiguous_THEN_reports_indeterminate_without_retrying():
    class AmbiguousGateway(FakeGateway):
        async def submit_draft(self, draft_id: str, title: str) -> GatewayResponse:
            self.calls.append(("submit", {"id": draft_id, "title": title}))
            return GatewayResponse(code="", indeterminate=True)

    gateway = AmbiguousGateway()
    result = asyncio.run(
        ArticlePublisher(gateway).publish(
            Article(title="A test article", blocks=(ArticleBlock.paragraph("Body"),))
        )
    )

    assert result.indeterminate
    assert [name for name, _ in gateway.calls].count("submit") == 1


def test_WHEN_submit_ack_lacks_remote_id_THEN_reports_indeterminate_without_verifying_or_retrying():
    class MissingIdGateway(FakeGateway):
        async def submit_draft(self, draft_id: str, title: str) -> GatewayResponse:
            self.calls.append(("submit", {"id": draft_id, "title": title}))
            return GatewayResponse(
                code="100000",
                data={"url": "https://weibo.com/ttarticle/p/show?id=article-1"},
            )

    gateway = MissingIdGateway()
    result = asyncio.run(
        ArticlePublisher(gateway).publish(
            Article(title="A test article", blocks=(ArticleBlock.paragraph("Body"),))
        )
    )

    assert result.indeterminate
    assert result.error_code == "indeterminate"
    assert result.diagnostics == {"step": "submit", "reason": "missing_remote_id"}
    assert "verify" not in [name for name, _ in gateway.calls]
    assert [name for name, _ in gateway.calls].count("submit") == 1
