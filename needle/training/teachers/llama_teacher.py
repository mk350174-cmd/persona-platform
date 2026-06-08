"""Llama local teacher (weight 0.2) via Ollama HTTP.

Talks to Ollama at ``{endpoint}/api/generate`` (default model ``llama3.2:3b``). If Ollama
is unreachable, ``available()`` returns False and the pipeline drops this teacher and
re-normalizes the remaining weights (falling back to PersonaMathTeacher if none remain).
"""

from __future__ import annotations

import httpx

from .base import BaseTeacher, conversation_text
from .claude_teacher import CEID_PROMPT, DRIFT_PROMPT, VOICE_PROMPT
from ._remote import JsonCache, clip01, extract_json, k_layer_summary, retry


class LlamaTeacher(BaseTeacher):
    name = "llama"
    weight = 0.2
    model = "llama3.2:3b"

    def __init__(self, endpoint: str = "http://localhost:11434", timeout: float = 60.0):
        self.endpoint = endpoint.rstrip("/")
        self._client = httpx.Client(timeout=timeout)
        self.cache = JsonCache("llama")

    def available(self) -> bool:
        try:
            r = self._client.get(f"{self.endpoint}/api/tags", timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False

    def _ask(self, prompt: str) -> str:
        cached = self.cache.get(prompt)
        if cached is not None:
            return cached

        def call():
            r = self._client.post(f"{self.endpoint}/api/generate",
                                  json={"model": self.model, "prompt": prompt, "stream": False})
            r.raise_for_status()
            return r.json().get("response", "")

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
