"""Phase 6: Unit tests for hybrid personas (HybridPersona model, matching, vector generation)."""

import json
import pytest
import numpy as np
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from unittest.mock import Mock

from api.db import SessionLocal, HybridPersona
from api.persona_matching_service import (
    build_hybrid_vector,
    build_neutral_vector,
    cosine_similarity,
    percentile_score,
    match_user_to_personas,
    _k_layer_cache,
)


# ──────────────────────────────────────────────────────────────────────
# Test: K-layer Vector Generation
# ──────────────────────────────────────────────────────────────────────

class TestHybridVectorGeneration:
    """Tests for K-layer vector construction."""

    def test_vector_shape(self):
        """Verify vector is 100-dimensional (canonical per GLOSSARY.md)."""
        persona = HybridPersona(
            id="test_shape",
            persona_id="komb_shape_test",
            combination_number=1,
            name_tr="Test",
            name_en="Test",
            use_case="Test",
            characteristic="Test",
            active_k_layers=[2, 12, 28, 71],
            suppressed_k_layers=[17, 81],
            price_usd=1499,
            is_available=True,
        )
        vector = build_hybrid_vector(persona)
        assert vector.shape == (100,), f"Expected shape (100,), got {vector.shape}"
        assert vector.dtype == np.float32

    def test_active_layers_weighted_correctly(self):
        """Test that active K-layers are weighted at 0.85."""
        persona = HybridPersona(
            id="test_active",
            persona_id="komb_active_test",
            combination_number=2,
            name_tr="Test",
            name_en="Test",
            use_case="Test",
            characteristic="Test",
            active_k_layers=[2, 12, 28, 71],
            suppressed_k_layers=[17, 81],
            price_usd=1499,
            is_available=True,
        )
        vector = build_hybrid_vector(persona)

        for layer in persona.active_k_layers:
            if 0 <= layer < 100:
                assert vector[layer] == 0.85, f"K-layer {layer} should be 0.85"

    def test_suppressed_layers_weighted_correctly(self):
        """Test that suppressed K-layers are weighted at 0.15."""
        persona = HybridPersona(
            id="test_suppressed",
            persona_id="komb_suppressed_test",
            combination_number=3,
            name_tr="Test",
            name_en="Test",
            use_case="Test",
            characteristic="Test",
            active_k_layers=[2, 12],
            suppressed_k_layers=[17, 81],
            price_usd=1499,
            is_available=True,
        )
        vector = build_hybrid_vector(persona)

        for layer in persona.suppressed_k_layers:
            if 0 <= layer < 100:
                assert vector[layer] == 0.15, f"K-layer {layer} should be 0.15"

    def test_neutral_layers_default_to_0_5(self):
        """Test that unmapped layers default to 0.5 (canonical 100-dim K-layers)."""
        persona = HybridPersona(
            id="test_neutral",
            persona_id="komb_neutral_test",
            combination_number=4,
            name_tr="Test",
            name_en="Test",
            use_case="Test",
            characteristic="Test",
            active_k_layers=[2, 12],
            suppressed_k_layers=[17, 81],
            price_usd=1499,
            is_available=True,
        )
        vector = build_hybrid_vector(persona)

        mapped_indices = set(persona.active_k_layers) | set(persona.suppressed_k_layers)

        for i in range(100):
            if i not in mapped_indices:
                assert vector[i] == 0.5, f"Unmapped K-layer {i} should be 0.5"

    def test_neutral_vector(self):
        """Test neutral vector is all 0.5 (canonical 100-dim)."""
        vector = build_neutral_vector()
        assert vector.shape == (100,), f"Expected shape (100,), got {vector.shape}"
        assert np.allclose(vector, 0.5)

    def test_empty_k_layers(self):
        """Test vector generation with empty K-layers."""
        persona = HybridPersona(
            id="test_empty",
            persona_id="komb_empty",
            combination_number=5,
            name_tr="Empty",
            name_en="Empty",
            use_case="Test",
            characteristic="Test",
            active_k_layers=[],
            suppressed_k_layers=[],
            price_usd=1499,
            is_available=True,
        )
        vector = build_hybrid_vector(persona)
        assert np.allclose(vector, 0.5)


# ──────────────────────────────────────────────────────────────────────
# Test: Cosine Similarity
# ──────────────────────────────────────────────────────────────────────

class TestCosineSimilarity:
    """Tests for cosine similarity calculations."""

    def test_identical_vectors(self):
        """Test identical vectors produce 1.0 similarity."""
        vector = np.full(98, 0.5, dtype=np.float32)
        user_vec = np.full(100, 0.5, dtype=np.float32)

        similarity = cosine_similarity(user_vec, vector)
        assert similarity == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        """Test orthogonal vectors."""
        user_vec = np.zeros(100, dtype=np.float32)
        user_vec[2:50] = 1.0

        persona_vec = np.zeros(98, dtype=np.float32)
        persona_vec[50:98] = 1.0

        similarity = cosine_similarity(user_vec, persona_vec)
        assert 0.0 <= similarity <= 1.0

    def test_opposite_vectors(self):
        """Test opposite vectors produce low similarity."""
        user_vec = np.full(100, 1.0, dtype=np.float32)
        persona_vec = np.full(98, 0.0, dtype=np.float32)

        similarity = cosine_similarity(user_vec, persona_vec)
        assert 0.0 <= similarity <= 0.5

    def test_similarity_range(self):
        """Test similarity is in [0, 1]."""
        user_vec = np.random.rand(100).astype(np.float32)
        persona_vec = np.random.rand(98).astype(np.float32)

        similarity = cosine_similarity(user_vec, persona_vec)
        assert 0.0 <= similarity <= 1.0

    def test_degenerate_case(self):
        """Test degenerate case with zero-norm vector."""
        user_vec = np.zeros(100, dtype=np.float32)
        persona_vec = np.full(98, 0.5, dtype=np.float32)

        similarity = cosine_similarity(user_vec, persona_vec)
        assert similarity == 0.5


# ──────────────────────────────────────────────────────────────────────
# Test: Percentile Score Conversion
# ──────────────────────────────────────────────────────────────────────

class TestPercentileScore:
    """Tests for similarity-to-percentile conversion."""

    def test_min_value(self):
        """Test similarity 0.0 converts to 0."""
        assert percentile_score(0.0) == 0

    def test_max_value(self):
        """Test similarity 1.0 converts to 100."""
        assert percentile_score(1.0) == 100

    def test_mid_value(self):
        """Test similarity 0.5 converts to 50."""
        assert percentile_score(0.5) == 50

    def test_bounded(self):
        """Test percentile is bounded to [0, 100]."""
        for sim in [-0.5, -1.0, 1.5, 2.0]:
            score = percentile_score(sim)
            assert 0 <= score <= 100

    def test_integer_result(self):
        """Test percentile is always an integer."""
        for sim in [0.0, 0.25, 0.5, 0.75, 1.0]:
            score = percentile_score(sim)
            assert isinstance(score, int)


# ──────────────────────────────────────────────────────────────────────
# Test: Top-5 Ranking
# ──────────────────────────────────────────────────────────────────────

class TestTop5Ranking:
    """Tests for ranking consistency."""

    def test_ranking_order_with_db(self):
        """Test top-5 personas are ordered descending."""
        db = SessionLocal()
        try:
            personas = db.query(HybridPersona).filter(
                HybridPersona.is_available == True
            ).limit(10).all()

            if len(personas) < 2:
                pytest.skip("Not enough personas")

            user_vec = np.full(100, 0.5, dtype=np.float32)
            top_id, top_5_ids, top_5_scores, _ = match_user_to_personas(
                user_vec.tolist(), db, top_k=5
            )

            if top_5_ids:
                assert top_id == top_5_ids[0]
                for i in range(len(top_5_scores) - 1):
                    assert top_5_scores[i] >= top_5_scores[i + 1]
        finally:
            db.close()

    def test_top_k_parameter(self):
        """Test top_k parameter limits results."""
        db = SessionLocal()
        try:
            count = db.query(HybridPersona).filter(
                HybridPersona.is_available == True
            ).count()

            if count < 2:
                pytest.skip("Not enough personas")

            user_vec = np.full(100, 0.5, dtype=np.float32)

            for k in [1, 3, 5]:
                _, top_5_ids, _, _ = match_user_to_personas(
                    user_vec.tolist(), db, top_k=k
                )
                expected = min(k, count)
                assert len(top_5_ids) == expected
        finally:
            db.close()


# ──────────────────────────────────────────────────────────────────────
# Test: Matching Flow
# ──────────────────────────────────────────────────────────────────────

class TestMatchingFlow:
    """Tests for matching workflow."""

    def test_no_personas_fallback(self):
        """Test fallback when no personas available."""
        db = Mock()
        db.query.return_value.filter.return_value.all.return_value = []

        user_vec = np.full(100, 0.5, dtype=np.float32)
        top_id, top_5_ids, _, profile = match_user_to_personas(
            user_vec.tolist(), db, top_k=5
        )

        assert top_id is None
        assert len(top_5_ids) == 0
        assert "error" in profile
        assert profile["is_historical"] == True

    def test_real_personas_matching(self):
        """Test matching against real personas."""
        db = SessionLocal()
        try:
            personas = db.query(HybridPersona).filter(
                HybridPersona.is_available == True
            ).all()

            if not personas:
                pytest.skip("No personas in DB")

            user_vec = np.full(100, 0.5, dtype=np.float32)
            top_id, top_5_ids, top_5_scores, _ = match_user_to_personas(
                user_vec.tolist(), db, top_k=5
            )

            assert top_id is not None
            assert len(top_5_ids) > 0
            assert all(0 <= s <= 100 for s in top_5_scores)
            assert top_id == top_5_ids[0]
        finally:
            db.close()


# ──────────────────────────────────────────────────────────────────────
# Test: API Response
# ──────────────────────────────────────────────────────────────────────

class TestAPIResponse:
    """Tests for API response format."""

    def test_profile_required_keys(self):
        """Test profile has all required keys."""
        db = SessionLocal()
        try:
            personas = db.query(HybridPersona).filter(
                HybridPersona.is_available == True
            ).all()

            if not personas:
                pytest.skip("No personas in DB")

            user_vec = np.full(100, 0.5, dtype=np.float32)
            _, _, _, profile = match_user_to_personas(user_vec.tolist(), db, top_k=5)

            required = [
                "user_vector_stats",
                "is_historical",
                "total_personas_compared",
                "top_k",
                "top_persona_details",
                "latency_ms",
                "cache_stats",
            ]

            for key in required:
                assert key in profile
        finally:
            db.close()

    def test_vector_stats(self):
        """Test vector stats are calculated."""
        db = SessionLocal()
        try:
            personas = db.query(HybridPersona).filter(
                HybridPersona.is_available == True
            ).all()

            if not personas:
                pytest.skip("No personas in DB")

            user_vec = np.array([0.1, 0.5, 0.9] * 33 + [0.5], dtype=np.float32)
            _, _, _, profile = match_user_to_personas(user_vec.tolist(), db, top_k=5)

            stats = profile["user_vector_stats"]
            assert "mean" in stats
            assert "std" in stats
            assert "min" in stats
            assert "max" in stats
            assert 0 <= stats["min"] <= 1
            assert 0 <= stats["max"] <= 1
        finally:
            db.close()

    def test_latency_recorded(self):
        """Test latency is recorded."""
        db = SessionLocal()
        try:
            personas = db.query(HybridPersona).filter(
                HybridPersona.is_available == True
            ).all()

            if not personas:
                pytest.skip("No personas in DB")

            user_vec = np.full(100, 0.5, dtype=np.float32)
            _, _, _, profile = match_user_to_personas(user_vec.tolist(), db, top_k=5)

            assert "latency_ms" in profile
            assert profile["latency_ms"] >= 0
        finally:
            db.close()


# ──────────────────────────────────────────────────────────────────────
# Test: K-Layer Cache
# ──────────────────────────────────────────────────────────────────────

class TestKLayerCache:
    """Tests for K-layer caching."""

    def test_cache_stats(self):
        """Test cache provides statistics."""
        stats = _k_layer_cache.stats()
        assert "size" in stats
        assert "maxsize" in stats
        assert "hits" in stats
        assert "misses" in stats

    def test_cache_operations(self):
        """Test cache put/get."""
        persona = HybridPersona(
            id="test_cache",
            persona_id="komb_cache_test",
            combination_number=10,
            name_tr="Cache Test",
            name_en="Cache Test",
            use_case="Test",
            characteristic="Test",
            active_k_layers=[2, 12],
            suppressed_k_layers=[81],
            price_usd=1499,
            is_available=True,
        )
        vector = build_hybrid_vector(persona)
        _k_layer_cache.put(persona.persona_id, vector)
        cached = _k_layer_cache.get(persona.persona_id)
        assert cached is not None
        np.testing.assert_array_equal(vector, cached)

    def test_maxsize_respected(self):
        """Test cache respects maxsize."""
        maxsize = _k_layer_cache.maxsize

        for i in range(maxsize + 5):
            key = f"test_key_{i}"
            vector = np.full(98, float(i) / 100, dtype=np.float32)
            _k_layer_cache.put(key, vector)

        stats = _k_layer_cache.stats()
        assert stats["size"] <= maxsize


# ──────────────────────────────────────────────────────────────────────
# Test: Database Integration
# ──────────────────────────────────────────────────────────────────────

class TestDatabaseIntegration:
    """Tests for database state."""

    def test_personas_in_database(self):
        """Verify personas are imported."""
        db = SessionLocal()
        try:
            count = db.query(HybridPersona).count()
            assert count >= 39
        finally:
            db.close()

    def test_no_duplicate_ids(self):
        """Verify no duplicate persona_ids."""
        db = SessionLocal()
        try:
            personas = db.query(HybridPersona).all()
            persona_ids = [p.persona_id for p in personas]
            assert len(persona_ids) == len(set(persona_ids))
        finally:
            db.close()

    def test_no_duplicate_numbers(self):
        """Verify no duplicate combination_numbers."""
        db = SessionLocal()
        try:
            personas = db.query(HybridPersona).all()
            numbers = [p.combination_number for p in personas]
            assert len(numbers) == len(set(numbers))
        finally:
            db.close()

    def test_k_layer_ranges_valid(self):
        """Verify K-layer indices are in [1, 98]."""
        db = SessionLocal()
        try:
            personas = db.query(HybridPersona).all()

            for p in personas:
                for layer in p.active_k_layers or []:
                    assert 1 <= layer <= 98
                for layer in p.suppressed_k_layers or []:
                    assert 1 <= layer <= 98
        finally:
            db.close()

    def test_required_fields_populated(self):
        """Verify required fields are populated."""
        db = SessionLocal()
        try:
            personas = db.query(HybridPersona).all()

            for p in personas:
                assert p.persona_id is not None
                assert p.combination_number is not None
                assert p.name_tr is not None
                assert p.name_en is not None
                assert p.use_case is not None
                assert p.characteristic is not None
        finally:
            db.close()

    def test_price_defaults(self):
        """Verify price_usd is set."""
        db = SessionLocal()
        try:
            personas = db.query(HybridPersona).all()

            for p in personas:
                assert p.price_usd is not None
                assert p.price_usd > 0
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not slow"])
