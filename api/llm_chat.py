"""NVIDIA NIM-backed chat completions (T2-019).

Gated behind ``NVIDIA_API_KEY`` — unconfigured, ``chat_available()`` is
False and callers (``persona_router.chat_websocket``) must stay honestly
echo-only rather than silently degrading (graceful-degradation pattern,
CLAUDE.md). Same OpenAI-compatible endpoint/pattern as
``needle/training/teachers/nvidia_teacher.py`` in the Persona repo —
verified 2026-08-12 against the real API (102 models live, real chat
completions returned).

The client is built lazily so this module imports without the ``openai``
SDK installed and without a key present.
"""

from __future__ import annotations

import os

_BASE_URL = "https://integrate.api.nvidia.com/v1"
_MODEL = "meta/llama-3.1-8b-instruct"

_client = None


def chat_available() -> bool:
    return bool(os.environ.get("NVIDIA_API_KEY"))


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI  # lazy
        _client = OpenAI(api_key=os.environ["NVIDIA_API_KEY"], base_url=_BASE_URL)
    return _client


def generate_reply(system_prompt: str, history: list[dict], user_message: str) -> str:
    """``history``: prior turns as ``[{"role": "user"|"assistant", "content": str}, ...]``."""
    messages = [{"role": "system", "content": system_prompt}, *history,
                {"role": "user", "content": user_message}]
    resp = _get_client().chat.completions.create(model=_MODEL, max_tokens=512, messages=messages)
    return resp.choices[0].message.content or ""
