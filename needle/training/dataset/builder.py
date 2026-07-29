"""
DatasetBuilder — turn (persona, conversation) into hybrid-labeled JSONL samples.

CEID/drift labels are the weighted average of the available teachers
(``final = Σ(w·label)/Σw``); ``confidence`` is the inter-teacher agreement
(1 − mean spread; a single teacher ⇒ 1.0). Voice samples are Claude-weighted (gold).
``build_full_dataset`` writes ceid/drift/voice JSONL with optional tqdm progress and a
resumable checkpoint.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import numpy as np

from ..teachers.base import BaseTeacher
from .conversation_generator import ConversationGenerator

_CEID_AXES = ("C", "E", "I", "D")

try:  # optional progress bar
    from tqdm import tqdm
except Exception:  # pragma: no cover
    def tqdm(it, **kw):
        return it


def _weighted(per_teacher: dict[str, dict], keys) -> dict:
    num = {k: 0.0 for k in keys}
    den = 0.0
    for name, (w, label) in per_teacher.items():
        for k in keys:
            num[k] += w * float(label[k])
        den += w
    return {k: round(num[k] / den, 4) for k in keys} if den else {k: 0.0 for k in keys}


def _confidence(per_teacher: dict[str, dict], keys) -> float:
    """1 − mean per-axis spread across teachers (single teacher ⇒ 1.0)."""
    if len(per_teacher) < 2:
        return 1.0
    spreads = []
    for k in keys:
        vals = [float(lbl[k]) for _, lbl in per_teacher.values()]
        spreads.append(max(vals) - min(vals))
    return round(1.0 - float(np.mean(spreads)), 4)


class DatasetBuilder:
    def __init__(self, teachers: list[BaseTeacher], generator: Optional[ConversationGenerator] = None):
        if not teachers:
            raise ValueError("DatasetBuilder needs at least one teacher")
        self.teachers = teachers
        self.gen = generator or ConversationGenerator()
        self._weight_sig = "_".join(f"{t.name}:{t.weight}" for t in teachers)

    # ── single samples ───────────────────────────────────────────────────────────
    def build_ceid_sample(self, persona_id: str, conversation, persona_vector=None) -> dict:
        per = {t.name: (t.weight, t.generate_ceid_labels(persona_id, persona_vector, conversation))
               for t in self.teachers}
        final = _weighted(per, _CEID_AXES)
        final["composite"] = round(float(np.mean([final[a] for a in _CEID_AXES])), 4)
        return {
            "persona_id": persona_id,
            "conversation": conversation["text"] if isinstance(conversation, dict) else conversation,
            "k_layer_vector": (list(np.asarray(persona_vector, float)) if persona_vector is not None else None),
            "ceid_labels": final,
            "teacher_scores": {n: lbl for n, (_, lbl) in per.items()},
            "confidence": _confidence(per, _CEID_AXES),
            "source": f"hybrid[{self._weight_sig}]",
        }

    def build_drift_sample(self, persona_id: str, conversation_before, conversation_after) -> dict:
        per = {t.name: (t.weight, t.generate_drift_label(persona_id, conversation_before, conversation_after))
               for t in self.teachers}
        score = round(sum(w * float(l["score"]) for _, (w, l) in [(n, v) for n, v in per.items()]) /
                      sum(w for w, _ in per.values()), 4)
        return {
            "persona_id": persona_id,
            "conversation_after": conversation_after["text"] if isinstance(conversation_after, dict) else conversation_after,
            "drift": bool(score > 0.5),
            "drift_score": score,
            "expected_drift": conversation_after.get("expected_drift") if isinstance(conversation_after, dict) else None,
            "teacher_scores": {n: l for n, (_, l) in per.items()},
            "source": f"hybrid[{self._weight_sig}]",
        }

    def build_voice_sample(self, persona_id: str, prompt: str, persona_vector=None) -> dict:
        # Claude-weighted gold: prefer the highest-weight teacher for the voice text.
        gold = max(self.teachers, key=lambda t: t.weight)
        return {
            "persona_id": persona_id,
            "prompt": prompt,
            "voice": gold.generate_voice_sample(persona_id, persona_vector, prompt),
            "teacher": gold.name,
            "source": f"voice[{gold.name}:{gold.weight}]",
        }

    def _build_one(self, pid: str, conv, pair, P: list) -> tuple:
        """Build the (ceid, drift, voice) samples for one conversation. Pure per-conversation
        work (teacher API calls) → safe to run in a worker thread; the per-teacher RateLimiter
        is thread-safe so concurrent workers still respect the rate limit."""
        ceid = self.build_ceid_sample(pid, conv, persona_vector=P)
        b, a = pair
        drift = self.build_drift_sample(pid, b, a)
        voice = self.build_voice_sample(pid, conv["text"] if isinstance(conv, dict) else conv, P)
        return ceid, drift, voice

    # ── full dataset (per-persona conversations built in parallel) ───────────────
    def build_full_dataset(self, personas: list[str], n_conversations: int = 20,
                           output_path: str = "needle/training/data/",
                           resume: bool = True, max_workers: int = 3) -> dict:
        from persona_math.persona_library import get_library_persona
        out = Path(output_path)
        out.mkdir(parents=True, exist_ok=True)
        ckpt_path = out / "build.ckpt.json"
        done = set(json.loads(ckpt_path.read_text())) if (resume and ckpt_path.exists()) else set()

        ceid_f = open(out / "ceid_dataset.jsonl", "a", encoding="utf-8")
        drift_f = open(out / "drift_dataset.jsonl", "a", encoding="utf-8")
        voice_f = open(out / "voice_dataset.jsonl", "a", encoding="utf-8")
        confs, n_ceid = [], 0
        try:
            for pid in tqdm(personas, desc="personas"):
                try:
                    P = np.asarray(get_library_persona(pid), float)
                except Exception:
                    P = np.zeros(100)
                Pl = P.tolist()
                convs = self.gen.generate(pid)[:n_conversations]
                pairs = self.gen.generate_pairs(pid)[:n_conversations]
                todo = [(j, conv) for j, conv in enumerate(convs) if f"{pid}#{j}" not in done]
                if not todo:
                    continue
                # build this persona's conversations concurrently (I/O-bound teacher calls)
                results: dict[int, tuple] = {}
                with ThreadPoolExecutor(max_workers=max_workers) as ex:
                    futs = {ex.submit(self._build_one, pid, conv, pairs[j], Pl): j
                            for j, conv in todo}
                    for fut in as_completed(futs):
                        results[futs[fut]] = fut.result()
                # write in conversation order → deterministic output (and stable checkpoints)
                for j in sorted(results):
                    ceid, drift, voice = results[j]
                    ceid_f.write(json.dumps(ceid, ensure_ascii=False) + "\n")
                    confs.append(ceid["confidence"]); n_ceid += 1
                    drift_f.write(json.dumps(drift, ensure_ascii=False) + "\n")
                    voice_f.write(json.dumps(voice, ensure_ascii=False) + "\n")
                    done.add(f"{pid}#{j}")
                ckpt_path.write_text(json.dumps(sorted(done)))
        finally:
            ceid_f.close(); drift_f.close(); voice_f.close()
        return {"personas": len(personas), "ceid_samples": n_ceid,
                "mean_confidence": round(float(np.mean(confs)), 4) if confs else None,
                "output_path": str(out)}
