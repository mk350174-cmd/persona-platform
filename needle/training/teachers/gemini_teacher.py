"""Gemini API teacher (weight 0.3) — structured output / second opinion.

Lazy ``import google.generativeai``. 15 req/min (free tier), 3-retry backoff, on-disk
cache. Reuses the Claude prompt set. Not run in this environment (no egress).
"""

from __future__ import annotations

from .base import BaseTeacher, conversation_text
from .claude_teacher import CEID_PROMPT, DRIFT_PROMPT, VOICE_PROMPT
from ._remote import JsonCache, RateLimiter, clip01, extract_json, k_layer_summary, retry


class GeminiTeacher(BaseTeacher):
    name = "gemini"
    weight = 0.3
    model = "gemini-2.0-flash"

    def __init__(self, api_key: str):
        import google.generativeai as genai  # lazy
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(self.model)
        self.rate = RateLimiter(15)
        self.cache = JsonCache("gemini")

    def available(self) -> bool:
        return bool(self.api_key)

    def _ask(self, prompt: str) -> str:
        cached = self.cache.get(prompt)
        if cached is not None:
            return cached

        def call():
            self.rate.wait()
            return self._model.generate_content(prompt).text

        text = retry(call)
        self.cache.set(prompt, text)
        return text

    def generate_ceid_labels(self, persona_id, persona_vector, conversation) -> dict:
        out = extract_json(self._ask(CEID_PROMPT.format(
            persona_id=persona_id, k_layer_summary=k_layer_summary(persona_vector),
            conversation=conversation_text(conversation))))
        return {a: clip01(out[a]) for a in ("C", "E", "I", "D")}

    def generate_drift_label(self, persona_id, conversation_before, conversation_after) -> dict:
        out = extract_json(self._ask(DRIFT_PROMPT.format(
            persona_id=persona_id, before=conversation_text(conversation_before),
            after=conversation_text(conversation_after))))
        return {"drift": bool(out["drift"]), "score": clip01(out["score"])}

    def generate_voice_sample(self, persona_id, persona_vector, prompt) -> str:
        return self._ask(VOICE_PROMPT.format(
            persona_id=persona_id, k_layer_summary=k_layer_summary(persona_vector),
            prompt=prompt)).strip()
