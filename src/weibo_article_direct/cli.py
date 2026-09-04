from __future__ import annotations

import argparse
import asyncio
import re
import sys
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path

from .auth import login_with_qr
from .http_client import OwnerHttpClient
from .live_gateway import LiveArticleGateway
from .models import Article, ArticleBlock
from .publisher import ArticlePublisher

_IMAGE_BLOCK = re.compile(r"^!\[(?P<caption>[^\]]*)\]\((?P<path>[^)]+)\)$")


def parse_article_body(path: Path) -> tuple[ArticleBlock, ...]:
    """Parse paragraphs and standalone Markdown image blocks from an UTF-8 file."""

    source = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    blocks: list[ArticleBlock] = []
    for raw_block in re.split(r"\n\s*\n", source):
        text = raw_block.strip()
        if not text:
            continue
        image = _IMAGE_BLOCK.fullmatch(text)
        if image:
            image_path = _resolve_media_path(path.parent, image.group("path"))
            blocks.append(ArticleBlock.image(str(image_path), caption=image.group("caption")))
        else:
            blocks.append(ArticleBlock.paragraph(text))
    if not blocks:
        raise ValueError("body file has no publishable content")
    return tuple(blocks)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="weibo-article",
        description="Owner-operated CLI for one Weibo headline article.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    publish = commands.add_parser("publish", help="scan QR and publish exactly one article")
    publish.add_argument("--title", required=True, help="article title")
    publish.add_argument("--body-file", required=True, type=Path, help="UTF-8 Markdown body file")
    publish.add_argument("--cover", type=Path, help="optional local cover image")
    publish.add_argument(
        "--confirm-publish",
        action="store_true",
        help="required acknowledgement before a real submit is allowed",
    )
    publish.add_argument("--login-timeout", type=int, default=180, help="QR login timeout in seconds")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _configure_console_encoding()
    args = build_parser().parse_args(argv)
    if args.command == "publish":
        return asyncio.run(_publish(args))
    return 2


async def _publish(args: argparse.Namespace) -> int:
    title = str(args.title).strip()
    if not title:
        print("发布已取消：标题不能为空。", file=sys.stderr)
        return 2
    try:
        body_path = Path(args.body_file).expanduser().resolve()
        blocks = parse_article_body(body_path)
        cover_path = _resolve_optional_cover(args.cover)
    except (OSError, ValueError) as exc:
        print(f"发布已取消：{exc}", file=sys.stderr)
        return 2
    if not args.confirm_publish:
        print(
            f"已检查文章：{title!r}，{len(blocks)} 个内容块。"
            "真实提交需要显式追加 --confirm-publish。"
        )
        return 2

    try:
        login = await login_with_qr(timeout_seconds=max(1, int(args.login_timeout)))
        async with OwnerHttpClient(login.cookies, user_agent=login.user_agent) as http:
            result = await ArticlePublisher(
                LiveArticleGateway(http=http, uid=login.uid)
            ).publish(Article(title=title, blocks=blocks, cover_path=cover_path))
    except (RuntimeError, TimeoutError) as exc:
        print(f"发布已取消：{exc}", file=sys.stderr)
        return 2
    if result.accepted and result.verified:
        print("发布并核验成功。")
        if result.remote_url:
            print(result.remote_url)
        return 0
    if result.indeterminate:
        print("提交结果不确定；为避免重复发布，CLI 已停止且未重试。", file=sys.stderr)
        return 3
    if result.blocked:
        print("平台要求额外验证；CLI 已停止。", file=sys.stderr)
        return 4
    if result.error_code == "draft_box_full":
        print("发布未完成：微博草稿箱已满（110002）。请打开微博头条文章草稿箱删除部分草稿后重试。", file=sys.stderr)
        return 1
    print(f"发布未完成：{result.error_code or 'platform_rejected'}。", file=sys.stderr)
    return 1


def _resolve_media_path(base: Path, value: str) -> Path:
    candidate = Path(value.strip()).expanduser()
    resolved = candidate if candidate.is_absolute() else base / candidate
    resolved = resolved.resolve()
    if not resolved.is_file():
        raise ValueError(f"image file does not exist: {resolved}")
    return resolved


def _resolve_optional_cover(value: Path | None) -> str | None:
    if value is None:
        return None
    resolved = Path(value).expanduser().resolve()
    if not resolved.is_file():
        raise ValueError(f"cover file does not exist: {resolved}")
    return str(resolved)


def _configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        with suppress(AttributeError, OSError):
            stream.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    raise SystemExit(main())
