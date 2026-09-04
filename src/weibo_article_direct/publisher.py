from __future__ import annotations

from contextlib import suppress
from html import escape

from .gateway import (
    ArticleGateway,
    DirectTransportUnavailable,
    DirectWriteIndeterminate,
)
from .models import Article, GatewayResponse, PublishResult

_SUCCESS_CODES = frozenset({"0", "100000"})


class ArticlePublisher:
    """Runs one article workflow exactly once through an authorized gateway."""

    def __init__(self, gateway: ArticleGateway) -> None:
        self._gateway = gateway

    async def publish(self, article: Article) -> PublishResult:
        if not article.title.strip():
            return PublishResult(False, False, error_code="invalid_article")

        draft_id = ""
        submit_dispatched = False

        async def cleanup_failed_draft() -> None:
            """Delete the network draft when the flow failed before submitting.

            The platform draft box has a hard capacity (30 on a standard
            account, verified 2026-09-04); leftover drafts from failed runs
            pile up until create_draft is rejected with 110002. Once the
            submit request is dispatched the draft may already be an article,
            so it is deliberately kept.
            """
            if not draft_id or submit_dispatched:
                return
            with suppress(Exception):
                await self._gateway.delete_draft(draft_id)

        try:
            created = await self._gateway.create_draft()
            failure = _failure("create", created)
            if failure:
                await cleanup_failed_draft()
                return failure
            draft_id = str(created.data.get("id") or "")
            if not draft_id:
                return PublishResult(False, False, error_code="invalid_response", diagnostics={"step": "create"})

            initial = await self._gateway.save_draft(
                draft_id,
                title=article.title,
                content=_render_article(article, {}),
                cover="",
                action="1",
                follow_to_read="0",
            )
            failure = _failure("save_initial", initial)
            if failure:
                await cleanup_failed_draft()
                return failure

            uploaded: dict[str, str] = {}
            for block in article.blocks:
                if block.local_media_path:
                    failure = await self._upload_and_attach(block.local_media_path, uploaded)
                    if failure:
                        return failure

            body_saved = await self._gateway.save_draft(
                draft_id,
                title=article.title,
                content=_render_article(article, uploaded),
                cover="",
                action="1",
                follow_to_read="0",
            )
            failure = _failure("save_body", body_saved)
            if failure:
                await cleanup_failed_draft()
                return failure

            cover_url = ""
            if article.cover_path:
                failure = await self._upload_and_attach(article.cover_path, uploaded)
                if failure:
                    await cleanup_failed_draft()
                    return failure
                cover_url = uploaded[article.cover_path]

            final_saved = await self._gateway.save_draft(
                draft_id,
                title=article.title,
                content=_render_article(article, uploaded),
                cover=cover_url,
                action="2",
                follow_to_read="0",
            )
            failure = _failure("save_final", final_saved)
            if failure:
                await cleanup_failed_draft()
                return failure

            loaded = await self._gateway.load_draft(draft_id)
            failure = _failure("load", loaded)
            if failure:
                await cleanup_failed_draft()
                return failure

            submitted = await self._gateway.submit_draft(draft_id, article.title)
            failure = _failure("submit", submitted)
            if failure:
                return failure
            submit_dispatched = True
            remote_id = str(submitted.data.get("object_id") or "").split(":")[-1] or None
            remote_url = str(submitted.data.get("url") or "") or None
            if not remote_id:
                return PublishResult(
                    False,
                    False,
                    indeterminate=True,
                    error_code="indeterminate",
                    diagnostics={"step": "submit", "reason": "missing_remote_id"},
                )
            verified = await self._gateway.verify_article(
                remote_id, article.title, remote_url
            )
            failure = _failure("verify", verified)
            if failure:
                await cleanup_failed_draft()
                return failure
            return PublishResult(True, True, remote_id=remote_id, remote_url=remote_url)
        except DirectWriteIndeterminate:
            return PublishResult(False, False, indeterminate=True, error_code="indeterminate")
        except DirectTransportUnavailable:
            return PublishResult(False, False, error_code="transport_unavailable")

    async def _upload_and_attach(self, path: str, uploaded: dict[str, str]) -> PublishResult | None:
        if path in uploaded:
            return None
        response = await self._gateway.upload_image(path)
        failure = _failure("upload", response)
        if failure:
            return failure
        image_url = str(response.data.get("url") or "")
        if not image_url:
            return PublishResult(False, False, error_code="invalid_response", diagnostics={"step": "upload"})
        attached = await self._gateway.attach_image(image_url)
        failure = _failure("attach", attached)
        if failure:
            return failure
        uploaded[path] = image_url
        return None


def _failure(step: str, response: GatewayResponse) -> PublishResult | None:
    if response.indeterminate:
        return PublishResult(False, False, indeterminate=True, error_code="indeterminate", diagnostics={"step": step})
    if response.blocked:
        return PublishResult(False, False, blocked=True, error_code="security_challenge", diagnostics={"step": step})
    if str(response.code) not in _SUCCESS_CODES:
        # 110002 = draft box full (capacity 30); give an actionable error.
        error_code = "draft_box_full" if str(response.code) == "110002" else "platform_rejected"
        return PublishResult(False, False, error_code=error_code, diagnostics={"step": step, "code": str(response.code)})
    return None


def _render_article(article: Article, uploaded: dict[str, str]) -> str:
    parts: list[str] = []
    for block in article.blocks:
        if block.kind == "paragraph" and block.text.strip():
            parts.append(f"<p>{escape(block.text)}</p>")
        elif block.kind == "image" and block.local_media_path in uploaded:
            caption = f"<figcaption>{escape(block.caption)}</figcaption>" if block.caption else ""
            parts.append(f'<figure><img src="{escape(uploaded[block.local_media_path])}" alt="">{caption}</figure>')
    return "".join(parts)
