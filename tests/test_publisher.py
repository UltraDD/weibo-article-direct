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


def test_WHEN_save_is_rejected_THEN_leftover_network_draft_is_deleted():
    """Regression 2026-09-04: failed runs left network drafts until the
    platform draft box (capacity 30) filled up and create was rejected
    with 110002. Failures before submit must delete the draft."""

    class CleanupGateway(FakeGateway):
        def __init__(self) -> None:
            super().__init__()
            self.deleted: list[str] = []

        async def save_draft(self, draft_id: str, **fields: str) -> GatewayResponse:
            self.calls.append(("save", {"id": draft_id, **fields}))
            if fields.get("action") == "2":
                return GatewayResponse(code="100001", message="save rejected")
            return GatewayResponse(code="100000")

        async def delete_draft(self, draft_id: str) -> GatewayResponse:
            self.deleted.append(draft_id)
            return GatewayResponse(code="100000")

        async def draft_usage(self) -> tuple[int, int]:
            return (1, 30)

    gateway = CleanupGateway()
    result = asyncio.run(
        ArticlePublisher(gateway).publish(
            Article(title="A test article", blocks=(ArticleBlock.paragraph("Body"),))
        )
    )
    assert result.accepted is False
    assert result.error_code == "platform_rejected"
    assert gateway.deleted == ["draft-1"]


def test_WHEN_publish_succeeds_THEN_network_draft_is_not_deleted():
    """A dispatched submit may already be an article; the draft is kept."""

    class SuccessGateway(FakeGateway):
        def __init__(self) -> None:
            super().__init__()
            self.deleted: list[str] = []

        async def delete_draft(self, draft_id: str) -> GatewayResponse:
            self.deleted.append(draft_id)
            return GatewayResponse(code="100000")

        async def draft_usage(self) -> tuple[int, int]:
            return (1, 30)

    gateway = SuccessGateway()
    result = asyncio.run(
        ArticlePublisher(gateway).publish(
            Article(title="A test article", blocks=(ArticleBlock.paragraph("Body"),))
        )
    )
    assert result.accepted and result.verified
    assert gateway.deleted == []


def test_WHEN_create_returns_110002_THEN_error_is_draft_box_full():
    """The full draft box must surface as an actionable draft_box_full."""

    class FullBoxGateway(FakeGateway):
        def __init__(self) -> None:
            super().__init__()
            self.deleted: list[str] = []

        async def create_draft(self) -> GatewayResponse:
            return GatewayResponse(code="110002", message="最大草稿个数达到上限")

        async def delete_draft(self, draft_id: str) -> GatewayResponse:
            self.deleted.append(draft_id)
            return GatewayResponse(code="100000")

        async def draft_usage(self) -> tuple[int, int]:
            return (30, 30)

    result = asyncio.run(
        ArticlePublisher(FullBoxGateway()).publish(
            Article(title="A test article", blocks=(ArticleBlock.paragraph("Body"),))
        )
    )
    assert result.accepted is False
    assert result.error_code == "draft_box_full"
