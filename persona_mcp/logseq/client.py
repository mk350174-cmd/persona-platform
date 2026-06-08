"""Logseq local HTTP API client (default port 12315).

Talks to Logseq's HTTP server: ``POST {base_url}`` with JSON ``{"method": ...,
"args": [...]}`` and an ``Authorization: Bearer <token>`` header. Any connection /
HTTP error is wrapped in ``LogseqUnavailable`` so callers (``PersonaGraph``) can fall
back to a local cache gracefully. Logseq method names may vary slightly by version;
adjust in one place here if needed.
"""

from __future__ import annotations

from typing import Any, Optional

import httpx

DEFAULT_BASE_URL = "http://localhost:12315/api"


class LogseqUnavailable(Exception):
    """Raised when the Logseq HTTP API cannot be reached."""


class LogseqClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, token: Optional[str] = None,
                 timeout: float = 5.0, transport: Optional[httpx.BaseTransport] = None):
        self.base_url = base_url
        self.token = token
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        # `transport` lets tests inject httpx.MockTransport (no real Logseq).
        self._client = httpx.Client(timeout=timeout, headers=headers, transport=transport)

    def _call(self, method: str, *args: Any) -> Any:
        try:
            resp = self._client.post(self.base_url, json={"method": method, "args": list(args)})
            resp.raise_for_status()
            return resp.json() if resp.content else None
        except Exception as exc:  # connection refused, timeout, HTTP error, bad JSON
            raise LogseqUnavailable(f"{method}: {exc}") from exc

    def available(self) -> bool:
        try:
            self._call("logseq.App.getInfo")
            return True
        except LogseqUnavailable:
            return False

    # ── pages / blocks ───────────────────────────────────────────────────────────
    def get_page(self, name: str) -> dict:
        return self._call("logseq.Editor.getPage", name)

    def create_page(self, name: str, content: str = "") -> dict:
        page = self._call("logseq.Editor.createPage", name, {}, {"redirect": False,
                                                                 "createFirstBlock": False})
        if content:
            self.append_block(name, content)
        return page

    def update_page(self, name: str, content: str) -> dict:
        # Logseq has no atomic page replace; append the new content as a block.
        return self.append_block(name, content)

    def append_block(self, page: str, content: str) -> dict:
        return self._call("logseq.Editor.appendBlockInPage", page, content)

    def query(self, query: str) -> list:
        return self._call("logseq.DB.datascriptQuery", query) or []

    def get_all_pages(self) -> list:
        return self._call("logseq.Editor.getAllPages") or []

    def close(self):
        self._client.close()
