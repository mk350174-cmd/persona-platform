"""Claude API teacher (weight 0.5) — persona depth + CEID gold standard.

Lazy ``import anthropic`` (module imports without the SDK). 60 req/min, 3-retry
exponential backoff, on-disk response cache. Not run in this environment (no egress).
"""

from __future__ import annotations

from .base import BaseTeacher, Conversation, conversation_text
from ._remote import JsonCache, RateLimiter, clip01, extract_json, k_layer_summary, retry

CEID_PROMPT = """Sen bir persona tutarlılık değerlendiricisin.

Persona: {persona_id}
K-layer özeti: {k_layer_summary}

Aşağıdaki konuşmayı analiz et ve CEID skorunu ver:
Konuşma: {conversation}

Sadece JSON döndür:
{{"C": <0.0-1.0, bağlam uyumu>, "E": <0.0-1.0, epistemik tutarlılık>, "I": <0.0-1.0, kimlik stabilitesi>, "D": <0.0-1.0, drift direnci>}}"""

DRIFT_PROMPT = """Bu iki konuşma arasında persona kimlik kayması var mı?

Persona: {persona_id}
Önceki: {before}
Sonraki: {after}

Sadece JSON döndür:
{{"drift": <true/false>, "score": <0.0-1.0>}}"""

VOICE_PROMPT = """Sen {persona_id} karakterisin.
K-layer profilin: {k_layer_summary}

Bu soruya karakterine uygun yanıt ver:
{prompt}

Sadece yanıtı döndür, meta-yorum yapma."""


class ClaudeTeacher(BaseTeacher):
    name = "claude"
    weight = 0.5
    model = "claude-sonnet-4-20250514"

    def __init__(self, api_key: str, max_tokens: int = 1024):
        import anthropic  # lazy
        self.api_key = api_key
        self.client = anthropic.Anthropic(api_key=api_key)
        self.max_tokens = max_tokens
        self.rate = RateLimiter(60)
        self.cache = JsonCache("claude")

    def available(self) -> bool:
        return bool(self.api_key)

    def _ask(self, prompt: str) -> str:
        cached = self.cache.get(prompt)
        if cached is not None:
            return cached

        def call():
            self.rate.wait()
            msg = self.client.messages.create(
                model=self.model, max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}])
            return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")

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
