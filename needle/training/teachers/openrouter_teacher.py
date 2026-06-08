"""OpenRouter teacher (weight 0.2, backup) — free Llama-70B via the OpenAI-compatible API.

Lazy ``from openai import OpenAI`` pointed at https://openrouter.ai/api/v1. Free models can
be rate-limited, so 5 req/min. On-disk cache, graceful persona_math fallback.
``available()`` ⇔ OPENROUTER_KEY present.
"""

from __future__ import annotations

from ._openai_chat import ChatCompletionsTeacher


class OpenRouterTeacher(ChatCompletionsTeacher):
    name = "openrouter"
    weight = 0.2
    base_url = "https://openrouter.ai/api/v1"
    model = "meta-llama/llama-3.1-70b-instruct:free"
    rpm = 5
    cache_namespace = "openrouter"

    def _build_client(self):
        from openai import OpenAI  # lazy
        return OpenAI(api_key=self.api_key, base_url=self.base_url)
