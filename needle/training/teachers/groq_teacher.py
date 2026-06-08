"""Groq teacher (weight 0.3) — fast Llama-70B, free (14,400 req/day).

Lazy ``from groq import Groq`` (imports without the SDK). The Groq client is OpenAI-shaped
(``client.chat.completions.create``), so it reuses ``ChatCompletionsTeacher``. 10 req/min
(safe), on-disk cache, graceful persona_math fallback. ``available()`` ⇔ GROQ_API_KEY present.
"""

from __future__ import annotations

from ._openai_chat import ChatCompletionsTeacher


class GroqTeacher(ChatCompletionsTeacher):
    name = "groq"
    weight = 0.3
    model = "llama-3.1-70b-versatile"
    rpm = 10
    cache_namespace = "groq"

    def _build_client(self):
        from groq import Groq  # lazy
        return Groq(api_key=self.api_key)
