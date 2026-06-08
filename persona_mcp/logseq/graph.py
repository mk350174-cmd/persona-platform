"""
PersonaGraph — persona knowledge-graph over Logseq with graceful degradation.

Every write attempts Logseq and **always** appends to a durable local cache
(``cache_dir/<persona_id>.*``), so reads work whether or not Logseq is running and the
tools never raise just because Logseq is down. Templates are rendered with jinja2.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .client import LogseqClient, LogseqUnavailable

_TEMPLATES = Path(__file__).parent / "templates"
_AXIS_MAP = {"C_semantic_resonance": "C", "E_epistemic_vigilance": "E",
             "I_tree_convergence": "I", "D_sarsılmazlık": "D"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PersonaGraph:
    def __init__(self, client: Optional[LogseqClient] = None,
                 cache_dir: str | Path = None):
        self.client = client
        self.cache_dir = Path(cache_dir) if cache_dir else (Path(__file__).resolve()
                                                            .parent.parent / ".cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._env = Environment(loader=FileSystemLoader(str(_TEMPLATES)),
                                autoescape=select_autoescape(enabled_extensions=()))

    # ── helpers ──────────────────────────────────────────────────────────────────
    def render(self, template: str, **ctx) -> str:
        return self._env.get_template(template).render(**ctx)

    def _try_logseq(self, fn) -> bool:
        """Run a Logseq write; return True if it succeeded, False on degradation."""
        if self.client is None:
            return False
        try:
            fn(self.client)
            return True
        except LogseqUnavailable:
            return False

    def _append_jsonl(self, pid: str, kind: str, record: dict) -> None:
        with open(self.cache_dir / f"{pid}.{kind}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _read_jsonl(self, pid: str, kind: str) -> list[dict]:
        path = self.cache_dir / f"{pid}.{kind}.jsonl"
        if not path.exists():
            return []
        return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    @staticmethod
    def _ceid_from_vector(P: np.ndarray) -> dict:
        from persona_math.ceid import ceid_score
        sc = ceid_score(P, P)
        axes = {_AXIS_MAP.get(k, k): round(float(v), 4) for k, v in sc["axes"].items()}
        axes["composite"] = round(float(sc["CEID_score"]), 4)
        return axes

    # ── writes ───────────────────────────────────────────────────────────────────
    def init_persona_page(self, persona_id: str) -> dict:
        from persona_math.persona_library import get_library_persona
        from persona_math.params import MANDATORY_CORE_INDICES
        try:
            P = np.asarray(get_library_persona(persona_id), dtype=float)
        except Exception:
            P = np.zeros(100, dtype=float)
        ceid = self._ceid_from_vector(P)
        core = list(MANDATORY_CORE_INDICES)
        page = self.render(
            "persona_page.md", persona_id=persona_id, domain="unknown",
            ceid_baseline=ceid["composite"], created_date=_now(),
            mandatory_core_score=round(float(P[core].mean()), 4),
            virtu_index=round(float(P[5]), 4),
            C=ceid["C"], E=ceid["E"], I=ceid["I"], D=ceid["D"],
            ceid_history="", drift_events="", conversation_memory="")
        (self.cache_dir / f"{persona_id}.md").write_text(page, encoding="utf-8")
        backend = "logseq" if self._try_logseq(
            lambda c: c.create_page(persona_id, page)) else "cache"
        return {"persona_id": persona_id, "ceid_baseline": ceid, "backend": backend}

    def log_ceid_measurement(self, persona_id: str, ceid_scores: dict,
                             untrained: bool = True, timestamp: Optional[str] = None) -> dict:
        ts = timestamp or _now()
        self._append_jsonl(persona_id, "ceid",
                           {"timestamp": ts, "untrained": bool(untrained), **ceid_scores})
        recent = self._read_jsonl(persona_id, "ceid")[-10:]
        comps = [r.get("composite", r.get("C", 0)) for r in recent]
        trend = round(float(np.mean(comps)), 4) if comps else None
        # untrained → yellow warning block; trained PersonaNeedle → green confirm block
        marker = "🟡" if untrained else "🟢"
        status = ("UNTRAINED — reference (persona_math); SAN not distilled" if untrained
                  else "TRAINED — PersonaNeedle")
        entry = self.render("ceid_entry.md", timestamp=ts,
                            C=ceid_scores.get("C"), E=ceid_scores.get("E"),
                            I=ceid_scores.get("I"), D=ceid_scores.get("D"),
                            composite=ceid_scores.get("composite"), trend=trend)
        block = f"- {marker} {status}\n  {entry.lstrip('- ').rstrip()}"
        backend = "logseq" if self._try_logseq(
            lambda c: c.append_block(persona_id, block)) else "cache"
        return {"trend": trend, "backend": backend, "untrained": bool(untrained),
                "marker": marker, "block": block}

    def log_drift_event(self, persona_id: str, drift_score: float, context: str = "") -> dict:
        ts = _now()
        self._append_jsonl(persona_id, "drift",
                           {"timestamp": ts, "score": drift_score, "context": context})
        block = f"- > 🔴 **DRIFT** {ts} :: score={drift_score} — {context} #drift-alert"
        backend = "logseq" if self._try_logseq(
            lambda c: c.append_block(persona_id, block)) else "cache"
        return {"backend": backend}

    def add_memory(self, persona_id: str, content: str, tags=None,
                   metadata: Optional[dict] = None) -> dict:
        ts = _now()
        self._append_jsonl(persona_id, "memory",
                           {"timestamp": ts, "content": content, "tags": tags,
                            "metadata": metadata})
        tag_str = " ".join(f"#{t}" for t in tags) if tags else ""
        block = self.render("conversation.md", timestamp=ts, content=content,
                            tags=tag_str, metadata=json.dumps(metadata) if metadata else "")
        backend = "logseq" if self._try_logseq(
            lambda c: c.append_block(persona_id, block)) else "cache"
        return {"backend": backend}

    # ── reads (from the durable cache) ───────────────────────────────────────────
    def get_ceid_history(self, persona_id: str, limit: int = 10) -> list[dict]:
        return self._read_jsonl(persona_id, "ceid")[-limit:]

    def get_drift_events(self, persona_id: str) -> list[dict]:
        return self._read_jsonl(persona_id, "drift")

    def get_memories(self, persona_id: str, limit: int = 10) -> list[dict]:
        return self._read_jsonl(persona_id, "memory")[-limit:]

    # ── bulk ─────────────────────────────────────────────────────────────────────
    def init_all_personas(self, limit: Optional[int] = None) -> dict:
        from persona_math.persona_library import PERSONA_LIBRARY
        ids = sorted(PERSONA_LIBRARY)
        if limit is not None:
            ids = ids[:limit]
        backends = {"logseq": 0, "cache": 0}
        for pid in ids:
            backends[self.init_persona_page(pid)["backend"]] += 1
        return {"initialized": len(ids), "backends": backends}
