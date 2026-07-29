"""Groq teacher (weight 0.3) — fast Llama-3.1-8B-Instant, free (high RPM).

Lazy ``from groq import Groq`` (imports without the SDK). The Groq client is OpenAI-shaped
(``client.chat.completions.create``), so it reuses ``ChatCompletionsTeacher``. 60 req/min
(the 8B-instant tier comfortably supports this → 1s/req), on-disk cache, graceful
persona_math fallback. ``available()`` ⇔ GROQ_API_KEY present.
"""

from __future__ import annotations

from ._openai_chat import ChatCompletionsTeacher


class GroqTeacher(ChatCompletionsTeacher):
    name = "groq"
    weight = 0.3
    model = "llama-3.1-8b-instant"     # 8B (was 70b-versatile): faster + higher RPM
    rpm = 60                           # 60/60 = 1s between requests (was 30 → 2s)
    cache_namespace = "groq"

    def _build_client(self):
        from groq import Groq  # lazy
        return Groq(api_key=self.api_key)
