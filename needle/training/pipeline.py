"""
TrainingPipeline — orchestrates dataset generation for PersonaNeedle.

Builds the available teacher set (reachable APIs / Ollama) and, if none are available,
falls back to the offline ``PersonaMathTeacher`` (so it never hard-crashes). Then builds
the dataset (checkpoint/resume), validates it, and writes stratified splits.

CLI:
  python -m needle.training.pipeline --claude-key $ANTHROPIC_API_KEY --n-conversations 20
  python -m needle.training.pipeline --limit 3            # offline fallback demo
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from .dataset.builder import DatasetBuilder
from .dataset.validator import DatasetValidator
from .dataset.splits import create_splits


class TrainingPipeline:
    def __init__(self, claude_api_key: Optional[str] = None, gemini_api_key: Optional[str] = None,
                 aiml_api_key: Optional[str] = None, groq_api_key: Optional[str] = None,
                 openrouter_api_key: Optional[str] = None,
                 llama_endpoint: str = "http://localhost:11434", offline_fallback: bool = True):
        teachers = []

        def _add(key, modpath, cls_name, label):
            if not key:
                return
            try:
                mod = __import__(f"needle.training.teachers.{modpath}", fromlist=[cls_name])
                teachers.append(getattr(mod, cls_name)(key))
            except Exception as exc:  # missing SDK / bad key
                print(f"[pipeline] {label} teacher unavailable: {exc}")

        # primary $0 hybrid: AIML 0.5 / Groq 0.3 / OpenRouter 0.2
        _add(aiml_api_key, "aiml_teacher", "AIMLTeacher", "AIML")
        _add(groq_api_key, "groq_teacher", "GroqTeacher", "Groq")
        _add(openrouter_api_key, "openrouter_teacher", "OpenRouterTeacher", "OpenRouter")
        # optional extras (Claude is pricey → skipped unless a key is given)
        _add(claude_api_key, "claude_teacher", "ClaudeTeacher", "Claude")
        _add(gemini_api_key, "gemini_teacher", "GeminiTeacher", "Gemini")
        if llama_endpoint:
            try:
                from .teachers.llama_teacher import LlamaTeacher
                lt = LlamaTeacher(llama_endpoint)
                if lt.available():
                    teachers.append(lt)
                else:
                    print("[pipeline] Llama/Ollama unreachable — dropping it")
            except Exception as exc:
                print(f"[pipeline] Llama teacher unavailable: {exc}")

        teachers = [t for t in teachers if t.available()]
        from .teachers.persona_math_teacher import PersonaMathTeacher
        if not teachers:
            if not offline_fallback:
                raise RuntimeError("no teachers available and offline_fallback disabled")
            print("[pipeline] no API teachers — using offline PersonaMathTeacher fallback")
            teachers = [PersonaMathTeacher(weight=1.0)]
        elif offline_fallback:
            # always include persona_math as a low-weight co-teacher: gives the dataset a
            # deterministic floor and an instant fallback signal when an API stalls/fails,
            # without waiting on rate limits
            teachers.append(PersonaMathTeacher(weight=0.1))
        self._normalize_weights(teachers)

        self.teachers = teachers
        self.builder = DatasetBuilder(teachers)

    @staticmethod
    def _normalize_weights(teachers: list) -> None:
        """Scale active teachers' weights to sum to 1.0 (sole teacher → 1.0)."""
        total = sum(float(getattr(t, "weight", 0.0)) for t in teachers)
        if total <= 0:
            for t in teachers:
                t.weight = 1.0 / len(teachers)
            return
        for t in teachers:
            t.weight = round(float(t.weight) / total, 6)

    def teacher_names(self) -> list[str]:
        return [t.name for t in self.teachers]

    def run(self, output_dir: str = "needle/training/data/",
            n_conversations_per_persona: int = 20, resume: bool = True,
            limit: Optional[int] = None) -> dict:
        from persona_math.persona_library import PERSONA_LIBRARY
        personas = sorted(PERSONA_LIBRARY)
        if limit is not None:
            personas = personas[:limit]
        build = self.builder.build_full_dataset(personas, n_conversations_per_persona,
                                                output_dir, resume=resume)
        ceid_path = Path(output_dir) / "ceid_dataset.jsonl"
        validation = DatasetValidator().validate_dataset(str(ceid_path))
        splits = create_splits(str(ceid_path))
        return {"teachers": self.teacher_names(), "build": build,
                "validation": validation, "splits": splits}


def main(argv=None) -> int:
    import os
    ap = argparse.ArgumentParser(description="PersonaNeedle training-data pipeline")
    # keys default to env vars, so `--aiml-key $AIMLAPI_KEY` and bare env both work
    ap.add_argument("--aiml-key", default=os.environ.get("AIMLAPI_KEY"))
    ap.add_argument("--groq-key", default=os.environ.get("GROQ_API_KEY"))
    ap.add_argument("--openrouter-key", default=os.environ.get("OPENROUTER_KEY"))
    ap.add_argument("--gemini-key", default=os.environ.get("GEMINI_API_KEY"))
    ap.add_argument("--claude-key", default=os.environ.get("ANTHROPIC_API_KEY"))
    ap.add_argument("--llama-endpoint", default="http://localhost:11434")
    ap.add_argument("--n-conversations", type=int, default=20)
    ap.add_argument("--output-dir", default="needle/training/data/")
    ap.add_argument("--limit", type=int, default=None, help="limit number of personas")
    ap.add_argument("--resume", action="store_true", help="resume from checkpoint")
    args = ap.parse_args(argv)

    pipe = TrainingPipeline(claude_api_key=args.claude_key, gemini_api_key=args.gemini_key,
                            aiml_api_key=args.aiml_key, groq_api_key=args.groq_key,
                            openrouter_api_key=args.openrouter_key,
                            llama_endpoint=args.llama_endpoint)
    print(f"[pipeline] active teachers: {pipe.teacher_names()}")
    stats = pipe.run(output_dir=args.output_dir, n_conversations_per_persona=args.n_conversations,
                     resume=args.resume, limit=args.limit)
    import json
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
