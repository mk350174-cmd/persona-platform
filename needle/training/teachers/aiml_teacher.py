"""AIML API teacher (weight 0.5) — Claude/GPT-quality via the OpenAI-compatible endpoint.

Single key reaches Claude/GPT/Gemini/Llama through https://api.aimlapi.com/v1. Lazy
``from openai import OpenAI`` (imports without the SDK). 60 req/min, on-disk cache,
graceful persona_math fallback. ``available()`` ⇔ a key is present (AIMLAPI_KEY).
"""

from __future__ import annotations

from ._openai_chat import ChatCompletionsTeacher


class AIMLTeacher(ChatCompletionsTeacher):
    name = "aiml"
    weight = 0.5
    base_url = "https://api.aimlapi.com/v1"
    model = "claude-3-5-sonnet-20241022"
    rpm = 60
    cache_namespace = "aiml"

    def _build_client(self):
        from openai import OpenAI  # lazy
        return OpenAI(api_key=self.api_key, base_url=self.base_url)
