from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

BlockKind = Literal["paragraph", "image"]


@dataclass(frozen=True, slots=True)
class ArticleBlock:
    kind: BlockKind
    text: str = ""
    local_media_path: str | None = None
    caption: str = ""

    @classmethod
    def paragraph(cls, text: str) -> ArticleBlock:
        return cls(kind="paragraph", text=text)

    @classmethod
    def image(cls, path: str, *, caption: str = "") -> ArticleBlock:
        return cls(kind="image", local_media_path=path, caption=caption)


@dataclass(frozen=True, slots=True)
class Article:
    title: str
    blocks: tuple[ArticleBlock, ...]
    cover_path: str | None = None


@dataclass(frozen=True, slots=True)
class GatewayResponse:
    """A normalized response from an owner-authenticated direct-session adapter."""

    code: str
    data: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    blocked: bool = False
    indeterminate: bool = False


@dataclass(frozen=True, slots=True)
class PublishResult:
    accepted: bool
    verified: bool
    remote_id: str | None = None
    remote_url: str | None = None
    indeterminate: bool = False
    blocked: bool = False
    error_code: str | None = None
    diagnostics: dict[str, str] = field(default_factory=dict)
