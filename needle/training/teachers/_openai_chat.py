"""
Shared base for OpenAI-style chat-completions teachers (AIML / OpenRouter / Groq).

Each subclass sets ``model`` + ``rpm`` + ``cache_namespace`` and implements
``_build_client()`` (lazy SDK import). The client is built **lazily** on first request, so
this module — and the subclasses — import cleanly without the ``openai`` / ``groq`` SDKs,
and ``available()`` only checks the key. On any API error a call gracefully falls back to
``PersonaMathTeacher`` (``persona_math.ceid``), so the pipeline never hard-fails.

Reuses the Claude prompt set (CEID / DRIFT / VOICE) and the ``_remote`` helpers
(rate-limit, on-disk cache, retry, JSON extraction).
"""

from __future__ import annotations

from .base import BaseTeacher, conversation_text
from .claude_teacher import CEID_PROMPT, DRIFT_PROMPT, VOICE_PROMPT
from ._remote import JsonCache, RateLimiter, clip01, extract_json, k_layer_summary, retry


class ChatCompletionsTeacher(BaseTeacher):
    """Teacher whose client exposes OpenAI-style ``client.chat.completions.create``."""

    model: str = ""
    rpm: int = 30
    cache_namespace: str = "chat"

    def __init__(self, api_key: str, max_tokens: int = 1024):
        self.api_key = api_key or ""
        self.max_tokens = max_tokens
        self.rate = RateLimiter(self.rpm)
        self.cache = JsonCache(self.cache_namespace)
        self._client = None

    # ── subclass hook: build the SDK client (lazy import inside) ──────────────────
    def _build_client(self):
        raise NotImplementedError

    @property
    def client(self):
        if self._client is None:
            self._client = self._build_client()       # SDK imported here, on first use
        return self._client

    def available(self) -> bool:
        return bool(self.api_key)

    def _ask(self, prompt: str) -> str:
        cached = self.cache.get(prompt)
        if cached is not None:
            return cached

        def call():
            self.rate.wait()
            resp = self.client.chat.completions.create(
                model=self.model, max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}])
            return resp.choices[0].message.content or ""

        text = retry(call)
        self.cache.set(prompt, text)
        return text

    @staticmethod
    def _fallback():
        from .persona_math_teacher import PersonaMathTeacher
        return PersonaMathTeacher()

    # ── labels (with per-call graceful fallback to persona_math.ceid) ─────────────
    def generate_ceid_labels(self, persona_id, persona_vector, conversation) -> dict:
        try:
            out = extract_json(self._ask(CEID_PROMPT.format(
                persona_id=persona_id, k_layer_summary=k_layer_summary(persona_vector),
                conversation=conversation_text(conversation))))
            return {a: clip01(out[a]) for a in ("C", "E", "I", "D")}
        except Exception:
            return self._fallback().generate_ceid_labels(persona_id, persona_vector, conversation)

    def generate_drift_label(self, persona_id, conversation_before, conversation_after) -> dict:
        try:
            out = extract_json(self._ask(DRIFT_PROMPT.format(
                persona_id=persona_id, before=conversation_text(conversation_before),
                after=conversation_text(conversation_after))))
            return {"drift": bool(out["drift"]), "score": clip01(out["score"])}
        except Exception:
            return self._fallback().generate_drift_label(
                persona_id, conversation_before, conversation_after)

    def generate_voice_sample(self, persona_id, persona_vector, prompt) -> str:
        try:
            return self._ask(VOICE_PROMPT.format(
                persona_id=persona_id, k_layer_summary=k_layer_summary(persona_vector),
                prompt=prompt)).strip()
        except Exception:
            return self._fallback().generate_voice_sample(persona_id, persona_vector, prompt)
