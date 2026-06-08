"""Abstract teacher interface for the PersonaNeedle distillation pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Union

import numpy as np

# A conversation passed to a teacher is either raw text or the ConversationGenerator
# record dict {"text","pressure","category",...}. Real (LLM) teachers read the text;
# the offline PersonaMathTeacher may also use the pressure metadata.
Conversation = Union[str, dict]


def conversation_text(conversation: Conversation) -> str:
    return conversation["text"] if isinstance(conversation, dict) else str(conversation)


class BaseTeacher(ABC):
    name: str = "base"
    weight: float = 0.0

    def available(self) -> bool:
        """Whether this teacher can serve requests (API reachable / keys present)."""
        return True

    @abstractmethod
    def generate_ceid_labels(self, persona_id: str, persona_vector: dict,
                             conversation: Conversation) -> dict:
        """→ {"C": 0..1, "E": 0..1, "I": 0..1, "D": 0..1}"""

    @abstractmethod
    def generate_drift_label(self, persona_id: str, conversation_before: Conversation,
                             conversation_after: Conversation) -> dict:
        """→ {"drift": bool, "score": 0..1}"""

    @abstractmethod
    def generate_voice_sample(self, persona_id: str, persona_vector: dict,
                              prompt: str) -> str:
        """→ a reply in the persona's voice (text)"""


def as_vector(persona_vector) -> np.ndarray:
    """Coerce a K-layer persona vector (ndarray / list / {'values': [...]}) to ndarray."""
    if isinstance(persona_vector, dict):
        persona_vector = persona_vector.get("values", list(persona_vector.values()))
    return np.asarray(persona_vector, dtype=float)
