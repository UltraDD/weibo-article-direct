from __future__ import annotations

from typing import Protocol

from .models import GatewayResponse


class DirectWriteIndeterminate(RuntimeError):
    """The write may have reached the platform; callers must not retry it."""


class DirectTransportUnavailable(RuntimeError):
    """The direct write was not sent because the local adapter was unavailable."""


class ArticleGateway(Protocol):
    """Owner-authenticated adapter for the platform's article editor workflow.

    Authentication is deliberately outside this public package. An application must
    obtain its own authorized session through the platform's normal login flow and
    implement this narrow protocol without exporting or importing credentials.
    """

    async def create_draft(self) -> GatewayResponse: ...

    async def save_draft(self, draft_id: str, **fields: str) -> GatewayResponse: ...

    async def upload_image(self, path: str) -> GatewayResponse: ...

    async def attach_image(self, image_url: str) -> GatewayResponse: ...

    async def load_draft(self, draft_id: str) -> GatewayResponse: ...

    async def submit_draft(self, draft_id: str, title: str) -> GatewayResponse: ...

    async def verify_article(
        self,
        remote_id: str,
        expected_title: str,
        remote_url: str | None = None,
    ) -> GatewayResponse: ...

    async def delete_draft(self, draft_id: str) -> GatewayResponse:
        """Delete a leftover network draft; failure is safe to ignore."""
        ...

    async def draft_usage(self) -> tuple[int, int]:
        """Return (used, capacity) of the platform draft box."""
        ...
