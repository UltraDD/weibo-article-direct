from __future__ import annotations

from pathlib import Path

from weibo_article_direct.cli import parse_article_body


def test_WHEN_markdown_has_a_standalone_image_THEN_cli_preserves_content_order(tmp_path: Path):
    image = tmp_path / "body.png"
    image.write_bytes(b"not a real image")
    body = tmp_path / "article.md"
    body.write_text("First paragraph.\n\n![Caption](body.png)\n\nLast paragraph.", encoding="utf-8")

    blocks = parse_article_body(body)

    assert [block.kind for block in blocks] == ["paragraph", "image", "paragraph"]
    assert blocks[1].caption == "Caption"
    assert blocks[1].local_media_path == str(image)
