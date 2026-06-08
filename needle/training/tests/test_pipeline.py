"""
PersonaNeedle training-pipeline tests — torch-free and SDK-free (mock + offline teachers).
"""

import json

import pytest

from needle.training.teachers.base import BaseTeacher
from needle.training.dataset.conversation_generator import (
    ConversationGenerator, CATEGORIES, LEVEL_NAMES)
from needle.training.dataset.builder import DatasetBuilder
from needle.training.dataset.validator import DatasetValidator
from needle.training.dataset.splits import create_splits
from needle.training import TrainingPipeline


class MockTeacher(BaseTeacher):
    def __init__(self, name, weight, ceid, drift_score=0.2):
        self.name, self.weight, self._ceid, self._ds = name, weight, ceid, drift_score

    def generate_ceid_labels(self, persona_id, persona_vector, conversation):
        return dict(self._ceid)

    def generate_drift_label(self, persona_id, before, after):
        return {"drift": self._ds > 0.5, "score": self._ds}

    def generate_voice_sample(self, persona_id, persona_vector, prompt):
        return f"[{self.name} voice for {persona_id}]"


# ── conversation generator ───────────────────────────────────────────────────────

def test_generator_produces_20_balanced():
    convs = ConversationGenerator(seed=1).generate("machiavelli")
    assert len(convs) == 20
    counts = {lvl: sum(c["pressure"] == lvl for c in convs) for lvl in (0, 1, 2, 3)}
    assert counts == {0: 5, 1: 5, 2: 5, 3: 5}                 # 4 levels × 5
    cats = {c["category"] for c in convs if c["pressure"] > 0}
    assert set(CATEGORIES) <= cats                            # all 4 pressure categories used


# ── builder: weighted average + confidence ───────────────────────────────────────

def test_weighted_average_exact():
    t1 = MockTeacher("a", 0.5, {"C": 0.8, "E": 0.8, "I": 0.8, "D": 0.8})
    t2 = MockTeacher("b", 0.5, {"C": 0.6, "E": 0.6, "I": 0.6, "D": 0.6})
    s = DatasetBuilder([t1, t2]).build_ceid_sample("p", "conv", persona_vector=[0.5] * 100)
    assert s["ceid_labels"]["C"] == pytest.approx(0.7)        # (.5*.8 + .5*.6)
    assert s["confidence"] == pytest.approx(0.8)              # 1 − spread(0.2)
    assert "hybrid" in s["source"]


def test_confidence_high_when_teachers_agree():
    t1 = MockTeacher("a", 0.6, {"C": 0.9, "E": 0.9, "I": 0.9, "D": 0.9})
    t2 = MockTeacher("b", 0.4, {"C": 0.9, "E": 0.9, "I": 0.9, "D": 0.9})
    s = DatasetBuilder([t1, t2]).build_ceid_sample("p", "conv", persona_vector=[0.5] * 100)
    assert s["confidence"] == pytest.approx(1.0)


# ── validator ──────────────────────────────────────────────────────────────────────

def test_validator_filters_low_confidence():
    v = DatasetValidator(confidence_threshold=0.7)
    data = [{"confidence": 0.9, "ceid_labels": {"C": .5, "E": .5, "I": .5, "D": .5},
             "k_layer_vector": [0.1] * 100},
            {"confidence": 0.4, "ceid_labels": {"C": .5, "E": .5, "I": .5, "D": .5},
             "k_layer_vector": [0.1] * 100}]
    assert len(v.filter_low_confidence(data)) == 1
    assert v.validate_ceid_sample(data[0]) is True
    assert v.validate_ceid_sample(data[1]) is False           # low confidence
    bad = {"confidence": 0.9, "ceid_labels": {"C": 1.5, "E": .5, "I": .5, "D": .5},
           "k_layer_vector": [0.1] * 100}
    assert v.validate_ceid_sample(bad) is False               # out of [0,1]


# ── splits ───────────────────────────────────────────────────────────────────────

def test_splits_ratios_stratified(tmp_path):
    path = tmp_path / "ceid_dataset.jsonl"
    with open(path, "w") as f:
        for pid in ("a", "b", "c"):
            for i in range(10):
                f.write(json.dumps({"persona_id": pid, "i": i}) + "\n")
    counts = create_splits(str(path), seed=1)
    assert counts["total"] == 30
    assert counts["train"] == 24 and counts["val"] == 3 and counts["test"] == 3
    for name in ("train", "val", "test"):
        assert (tmp_path / f"{name}.jsonl").exists()


# ── pipeline: single offline teacher, end-to-end ─────────────────────────────────

def test_pipeline_offline_runs(tmp_path):
    pipe = TrainingPipeline()                                  # no keys → PersonaMathTeacher
    assert pipe.teacher_names() == ["persona_math"]
    stats = pipe.run(output_dir=str(tmp_path), n_conversations_per_persona=4, limit=2)
    assert stats["build"]["ceid_samples"] == 8                # 2 personas × 4
    assert stats["validation"]["total"] == 8
    assert stats["splits"]["total"] == 8
    for fn in ("ceid_dataset.jsonl", "drift_dataset.jsonl", "voice_dataset.jsonl"):
        assert (tmp_path / fn).exists()


def test_checkpoint_resume_no_duplicates(tmp_path):
    TrainingPipeline().run(output_dir=str(tmp_path), n_conversations_per_persona=3, limit=1)
    n1 = sum(1 for _ in open(tmp_path / "ceid_dataset.jsonl"))
    TrainingPipeline().run(output_dir=str(tmp_path), n_conversations_per_persona=3, limit=1, resume=True)
    n2 = sum(1 for _ in open(tmp_path / "ceid_dataset.jsonl"))
    assert n1 == 3 and n2 == 3                                # resume skipped already-built


def test_graceful_degradation_all_apis_down(tmp_path):
    pipe = TrainingPipeline(claude_api_key=None, gemini_api_key=None,
                            llama_endpoint="http://localhost:1")  # nothing reachable
    assert pipe.teacher_names() == ["persona_math"]
    stats = pipe.run(output_dir=str(tmp_path), n_conversations_per_persona=2, limit=1)
    assert stats["build"]["ceid_samples"] == 2                # still produces data, no error
