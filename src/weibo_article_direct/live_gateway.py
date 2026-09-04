from __future__ import annotations

import re
import time
import zlib
from html import escape
from pathlib import Path
from typing import Protocol

from .http_client import CARD_ORIGIN, HttpResponse, is_trusted_weibo_url
from .models import GatewayResponse
from .request_id import build_request_id

_CREATE_PATH = "/article/v5/aj/editor/draft/create"
_SAVE_PATH = "/article/v5/aj/editor/draft/save"
_LOAD_PATH = "/article/v5/aj/editor/draft/load"
_DRAFT_DELETE_PATH = "/article/v5/aj/editor/draft/delete"
_DRAFT_LIST_PATH = "/article/v5/aj/editor/draft/list"
_PUBLISH_PATH = "/article/v5/aj/editor/draft/publish"
_ATTACH_PATH = "/article/v5/aj/editor/plugins/uploadpic"
_UPLOAD_URL = "https://picupload.weibo.com/interface/pic_upload.php"
_SUCCESS_CODES = frozenset({"0", "100000"})
_PID_PATTERN = re.compile(r'"pid"\s*:\s*"([A-Za-z0-9_-]+)"')
_URL_PATTERN = re.compile(
    r"https://\w+\.sinaimg\.cn/(?:large|mw1024|mw690|bmiddle)/[A-Za-z0-9._-]+\.(?:jpg|jpeg|png|gif|webp)"
)


class HttpClient(Protocol):
    async def request(self, method: str, url: str, **kwargs: object) -> HttpResponse: ...


class LiveArticleGateway:
    """Concrete, owner-only adapter for one article editor workflow."""

    def __init__(self, *, http: HttpClient, uid: str) -> None:
        self._http = http
        self._uid = str(uid)
        self._pid_by_url: dict[str, str] = {}
        self._draft_data: dict[str, dict[str, object]] = {}

    async def create_draft(self) -> GatewayResponse:
        response = await self._http.request(
            "POST",
            f"{CARD_ORIGIN}{_CREATE_PATH}",
            params={"uid": self._uid, "_rid": self._rid()},
            form={},
        )
        return _normalize(response)

    async def save_draft(self, draft_id: str, **fields: str) -> GatewayResponse:
        form = _save_form(draft_id, fields)
        response = await self._http.request(
            "POST",
            f"{CARD_ORIGIN}{_SAVE_PATH}",
            params={"uid": self._uid, "id": draft_id, "_rid": self._rid()},
            form=form,
        )
        return _normalize(response)

    async def upload_image(self, path: str) -> GatewayResponse:
        image = Path(path)
        if not image.is_file():
            return GatewayResponse(code="invalid_image", message="image file does not exist")
        data = image.read_bytes()
        content_type = _image_content_type(data)
        if not content_type:
            return GatewayResponse(code="invalid_image", message="unsupported image format")
        response = await self._http.request(
            "POST",
            _UPLOAD_URL,
            params={
                "app": "miniblog",
                "s": "json",
                "p": "1",
                "data": "1",
                "file_source": "4",
                "url": "0",
                "markpos": "1",
                "logo": "",
                "nick": "0",
                "_rid": self._rid(),
            },
            data=data,
            extra_headers={"Content-Type": content_type},
        )
        if _is_blocked(response):
            return GatewayResponse(code=str(response.status), blocked=True)
        pid = _extract_pid(response)
        image_url = _extract_image_url(response)
        code = str((response.payload or {}).get("code") or "") if isinstance(response.payload, dict) else ""
        if code != "A00006" or not pid or not image_url:
            return GatewayResponse(code=code or str(response.status), message="image upload rejected")
        self._pid_by_url[image_url] = pid
        return GatewayResponse(code="100000", data={"url": image_url})

    async def attach_image(self, image_url: str) -> GatewayResponse:
        pid = self._pid_by_url.get(image_url, "")
        if not pid:
            return GatewayResponse(code="invalid_image", message="upload receipt is missing")
        response = await self._http.request(
            "POST",
            f"{CARD_ORIGIN}{_ATTACH_PATH}",
            params={"_rid": self._rid()},
            form={"pid": pid, "uid": self._uid},
        )
        return _normalize(response)

    async def delete_draft(self, draft_id: str) -> GatewayResponse:
        response = await self._http.request(
            "POST",
            f"{CARD_ORIGIN}{_DRAFT_DELETE_PATH}",
            params={"uid": self._uid, "_rid": self._rid()},
            form={"uid": self._uid, "id": draft_id},
        )
        return _normalize(response)

    async def draft_usage(self) -> tuple[int, int]:
        response = await self._http.request(
            "POST",
            f"{CARD_ORIGIN}{_DRAFT_LIST_PATH}",
            params={"uid": self._uid},
            form={"uid": self._uid},
        )
        normalized = _normalize(response)
        used = int(normalized.data.get("count") or 0)
        cap = int(normalized.data.get("max_count") or 30)
        return used, cap

    async def load_draft(self, draft_id: str) -> GatewayResponse:
        response = await self._http.request(
            "GET",
            f"{CARD_ORIGIN}{_LOAD_PATH}",
            params={"uid": self._uid, "id": draft_id},
        )
        normalized = _normalize(response)
        if _is_success(normalized):
            self._draft_data[draft_id] = dict(normalized.data)
        return normalized

    async def submit_draft(self, draft_id: str, title: str) -> GatewayResponse:
        draft = self._draft_data.get(draft_id)
        if draft is None:
            return GatewayResponse(code="missing_draft_state", message="load_draft must run first")
        response = await self._http.request(
            "POST",
            f"{CARD_ORIGIN}{_PUBLISH_PATH}",
            params={"uid": self._uid, "id": draft_id, "_rid": self._rid()},
            form=_publish_form(draft_id, title, draft, self._uid),
        )
        return _normalize(response)

    async def verify_article(
        self, remote_id: str, expected_title: str, remote_url: str | None = None
    ) -> GatewayResponse:
        if not remote_url:
            return GatewayResponse(code="", indeterminate=True, message="publish response has no article URL")
        if not is_trusted_weibo_url(remote_url):
            return GatewayResponse(
                code="unsafe_verify_url",
                indeterminate=True,
                message="fresh-read URL is outside the trusted Weibo hosts",
            )
        response = await self._http.request("GET", remote_url)
        if _is_blocked(response):
            return GatewayResponse(code=str(response.status), blocked=True)
        if response.status != 200:
            return GatewayResponse(code=str(response.status), message="fresh read rejected")
        if expected_title not in response.body_text and escape(expected_title) not in response.body_text:
            return GatewayResponse(code="title_mismatch", message="fresh read did not match title")
        return GatewayResponse(code="100000", data={"id": remote_id})

    def _rid(self) -> str:
        return build_request_id(self._uid)


def _save_form(draft_id: str, fields: dict[str, str]) -> dict[str, str]:
    return {
        "save": "1",
        "id": draft_id,
        "title": str(fields["title"]),
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "free_content": "",
        "content": str(fields["content"]),
        "cover": str(fields["cover"]),
        "summary": "",
        "writer": "",
        "extra": "[]",
        "type": "",
        "is_word": "0",
        "is_markdown": "0",
        "article_recommend": "{}",
        "status": "0",
        "error_msg": "",
        "error_code": "0",
        "publish_at": "",
        "publish_local_at": "",
        "timestamp": "",
        "is_article_free": "0",
        "only_render_h5": "0",
        "is_ai_plugins": "0",
        "is_aigc_used": "0",
        "is_v4": "1",
        "follow_to_read": str(fields.get("follow_to_read", "0")),
        "follow_to_read_detail[result]": "0",
        "follow_to_read_detail[x]": "0",
        "follow_to_read_detail[y]": "0",
        "follow_to_read_detail[readme_link]": "",
        "follow_to_read_detail[level]": "",
        "follow_to_read_detail[daily_limit]": "1",
        "follow_to_read_detail[daily_limit_notes]": "",
        "follow_to_read_detail[show_level_tips]": "0",
        "isreward": "0",
        "isreward_tips": "",
        "isreward_tips_url": "",
        "pay_setting": "{\"ispay\":0,\"isvclub\":0,\"is_single_pay\":0,\"single_price\":0}",
        "source": "",
        "action": str(fields["action"]),
        "is_single_pay_new": "0",
        "money": "0",
        "is_vclub_single_pay": "0",
        "vclub_single_pay_money": "0",
        "content_type": "0",
        "sp_fid": "",
        "collection": "[]",
        "ver": "4.0",
    }


def _publish_form(draft_id: str, title: str, draft: dict[str, object], uid: str) -> dict[str, str]:
    aigc_used = str(draft.get("is_aigc_used") or "0")
    form = {
        "uid": uid,
        "id": draft_id,
        "text": f"发布了头条文章：《{title}》 ",
        "rank": "0",
        "mblog_statement": "1" if aigc_used not in {"", "0"} else "0",
        "sync_wb": "0",
        "is_original": "0",
        "time": "",
        "support_all_tag": "1",
        "ver": "4.0",
        "follow_official": "0",
        "timestamp": "",
        "only_render_h5": str(draft.get("only_render_h5") or "0"),
        "is_aigc_used": aigc_used,
        "follow_to_read": "0",
        "mpkey": "0",
    }
    imported = draft.get("import")
    if imported not in {None, "", "null"}:
        form["import"] = str(imported)
    return form


def _normalize(response: HttpResponse) -> GatewayResponse:
    payload = response.payload if isinstance(response.payload, dict) else {}
    code = str(payload.get("code", response.status))
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    return GatewayResponse(code=code, data=data, message=str(payload.get("msg") or ""), blocked=_is_blocked(response))


def _is_success(response: GatewayResponse) -> bool:
    return not response.blocked and not response.indeterminate and response.code in _SUCCESS_CODES


def _is_blocked(response: HttpResponse) -> bool:
    return response.status in {401, 403, 418, 429}


def _image_content_type(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return ""


def _extract_pid(response: HttpResponse) -> str:
    match = _PID_PATTERN.search(response.body_text)
    return match.group(1) if match else ""


def _extract_image_url(response: HttpResponse) -> str:
    text = response.body_text.replace("\\/", "/")
    urls = _URL_PATTERN.findall(text)
    if urls:
        return next((url for url in urls if "/large/" in url), urls[0])
    pid = _extract_pid(response)
    if not pid:
        return ""
    return _pid_to_url(pid)


def _pid_to_url(pid: str) -> str:
    if len(pid) > 9 and pid[9] in {"w", "y"}:
        server = 1 + (zlib.crc32(pid.encode("utf-8")) & 3)
        prefix = "ww" if pid[9] == "w" else "wx"
        extension = "gif" if len(pid) > 21 and pid[21] == "g" else "jpg"
        return f"https://{prefix}{server}.sinaimg.cn/large/{pid}.{extension}"
    try:
        server = 1 + (int(pid[-2:], 16) & 15)
    except ValueError:
        server = 1
    return f"https://ss{server}.sinaimg.cn/large/{pid}&690"
