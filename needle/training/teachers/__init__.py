"""Distillation teachers.

Hybrid set: AIML 0.5 / Groq 0.3 / OpenRouter 0.2 (all $0 / free-tier, OpenAI-compatible),
with optional Claude (0.5) / Gemini (0.3) / Llama (Ollama) and the offline PersonaMathTeacher
fallback. Active teachers' weights are normalized by the pipeline. All SDK imports are lazy
(torch-free, SDK-free to import)."""
from .base import BaseTeacher, conversation_text, as_vector
from .persona_math_teacher import PersonaMathTeacher
from .claude_teacher import ClaudeTeacher
from .gemini_teacher import GeminiTeacher
from .llama_teacher import LlamaTeacher
from .aiml_teacher import AIMLTeacher
from .groq_teacher import GroqTeacher
from .openrouter_teacher import OpenRouterTeacher

__all__ = ["BaseTeacher", "conversation_text", "as_vector", "PersonaMathTeacher",
           "ClaudeTeacher", "GeminiTeacher", "LlamaTeacher",
           "AIMLTeacher", "GroqTeacher", "OpenRouterTeacher"]
