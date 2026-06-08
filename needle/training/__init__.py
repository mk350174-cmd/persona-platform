"""PersonaNeedle training-data pipeline (teachers → hybrid-labeled JSONL → splits).

Imports without the teacher SDKs (anthropic/google-generativeai); those load only when
a remote teacher is constructed. The offline PersonaMathTeacher needs no network.
"""
from .pipeline import TrainingPipeline
from .dataset import ConversationGenerator, DatasetBuilder, DatasetValidator, create_splits
from .teachers import (BaseTeacher, PersonaMathTeacher, ClaudeTeacher, GeminiTeacher, LlamaTeacher)

__version__ = "0.1.0"
__all__ = ["TrainingPipeline", "ConversationGenerator", "DatasetBuilder", "DatasetValidator",
           "create_splits", "BaseTeacher", "PersonaMathTeacher", "ClaudeTeacher",
           "GeminiTeacher", "LlamaTeacher"]
