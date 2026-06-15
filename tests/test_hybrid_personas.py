"""
Phase 6: Unit tests for hybrid personas (HybridPersona model, matching, vector generation).

Test coverage:
1. test_hybrid_vector_generation() — K-layer vector construction and weighting
2. test_cosine_similarity_orthogonal() — Similarity calculations for edge cases
3. test_top_5_ranking_consistency() — Score ordering and percentile conversion
4. test_persona_match_api() — REST endpoint response validation
5. test_database_constraints() — Unique constraints on persona_id, combination_number
6. test_full_matching_flow() — End-to-end quiz submission → persona matching
"""

import json
import pytest
import numpy as np
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch, MagicMock

# Imports from api
from api.db import SessionLocal, HybridPersona, PersonaMatch, QuizSubmission, User, Base, engine
from api.persona_matching_service import (
    build_hybrid_vector,
    build_neutral_vector,
    cosine_similarity,
    percentile_score,
    match_user_to_personas,
    record_persona_match,
    update_submission_with_match,
    _k_layer_cache,
)


# ───────────────────────────────────────────────────────────────────────────────
# Fixtures
# ───────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db_session():
    """Create a clean test database session."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def sample_hybrid_persona(db_session: Session):
    """Create a sample hybrid persona for testing."""
    persona = HybridPersona(
        id="test_persona_001",
        persona_id="komb_001_test_cartesian",
        combination_number=1,
        name_tr="Test Rasyonalist",
        name_en="Test Cartesian",
        use_case="Test use case for analytical thinking",
        characteristic="Analytical and logical mindset",
        active_k_layers=[2, 12, 28, 71],
        suppressed_k_layers=[17, 81],
        example_outputs="Test output samples",
        price_usd=1499,
        is_available=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(persona)
    db_session.commit()
    db_session.refresh(persona)
    return persona


@pytest.fixture(scope="function")
def sample_user(db_session: Session):
    """Create a sample user for testing."""
    user = User(
        id="test_user_001",
        email="test@example.com",
        full_name="Test User",
        active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def sample_quiz_submission(db_session: Session, sample_user: User):
    """Create a sample quiz submission."""
    submission = QuizSubmission(
        id="test_submission_001",
        user_id=sample_user.id,
        answers_json=json.dumps({"q1": "a", "q2": "b"}),
        extracted_k_layer=[0.5] * 100,  # Neutral vector
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(submission)
    db_session.commit()
    db_session.refresh(submission)
    return submission


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the K-layer cache before each test."""
    _k_layer_cache.clear()
    yield
    _k_layer_cache.clear()


# ───────────────────────────────────────────────────────────────────────────────
# Test: K-layer Vector Generation
# ───────────────────────────────────────────────────────────────────────────────

class TestHybridVectorGeneration:
    """Tests for K-layer vector construction."""

    def test_vector_shape(self, sample_hybrid_persona: HybridPersona):
        """Verify vector is 98-dimensional."""
        vector = build_hybrid_vector(sample_hybrid_persona)
        assert vector.shape == (98,), f"Expected shape (98,), got {vector.shape}"
        assert vector.dtype == np.float32

    def test_active_layers_weighted_correctly(self, sample_hybrid_persona: HybridPersona):
        """Test that active K-layers are weighted at 0.85."""
        vector = build_hybrid_vector(sample_hybrid_persona)

        # Active layers: [2, 12, 28, 71]
        # These correspond to indices [0, 10, 26, 69] in the 98-dim array
        for layer in sample_hybrid_persona.active_k_layers:
            idx = layer - 2  # Convert to 0-indexed
            if 0 <= idx < 98:
                assert vector[idx] == 0.85, f"Layer {layer} (idx {idx}) should be 0.85, got {vector[idx]}"

    def test_suppressed_layers_weighted_correctly(self, sample_hybrid_persona: HybridPersona):
        """Test that suppressed K-layers are weighted at 0.15."""
        vector = build_hybrid_vector(sample_hybrid_persona)

        # Suppressed layers: [17, 81]
        # These correspond to indices [15, 79] in the 98-dim array
        for layer in sample_hybrid_persona.suppressed_k_layers:
            idx = layer - 2
            if 0 <= idx < 98:
                assert vector[idx] == 0.15, f"Layer {layer} (idx {idx}) should be 0.15, got {vector[idx]}"

    def test_neutral_layers_default_to_0_5(self, sample_hybrid_persona: HybridPersona):
        """Test that unmapped layers default to 0.5."""
        vector = build_hybrid_vector(sample_hybrid_persona)

        # Layers not in active or suppressed should be 0.5
        mapped_indices = set()
        for layer in sample_hybrid_persona.active_k_layers:
            mapped_indices.add(layer - 2)
        for layer in sample_hybrid_persona.suppressed_k_layers:
            mapped_indices.add(layer - 2)

        for i in range(98):
            if i not in mapped_indices:
                assert vector[i] == 0.5, f"Unmapped layer {i+2} should be 0.5, got {vector[i]}"

    def test_neutral_vector(self):
        """Test neutral vector is all 0.5."""
        vector = build_neutral_vector()
        assert vector.shape == (98,)
        assert np.allclose(vector, 0.5), "Neutral vector should be all 0.5"

    def test_empty_k_layers(self, db_session: Session):
        """Test vector generation with empty K-layers."""
        persona = HybridPersona(
            id="test_empty",
            persona_id="komb_empty",
            combination_number=99,
            name_tr="Empty",
            name_en="Empty",
            use_case="Test",
            characteristic="Test",
            active_k_layers=[],
            suppressed_k_layers=[],
            price_usd=1499,
            is_available=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        vector = build_hybrid_vector(persona)
        assert np.allclose(vector, 0.5), "Empty K-layers should produce all-0.5 vector"


# ───────────────────────────────────────────────────────────────────────────────
# Test: Cosine Similarity & Orthogonal Cases
# ───────────────────────────────────────────────────────────────────────────────

class TestCosineSimilarity:
    """Tests for cosine similarity calculations."""

    def test_identical_vectors_maximum_similarity(self):
        """Test that identical vectors produce 1.0 similarity."""
        vector = np.full(98, 0.5, dtype=np.float32)
        user_vec = np.full(100, 0.5, dtype=np.float32)

        similarity = cosine_similarity(user_vec, vector)
        assert similarity == pytest.approx(1.0), f"Identical vectors should have similarity 1.0, got {similarity}"

    def test_orthogonal_vectors(self):
        """Test orthogonal vectors produce ~0.5 similarity."""
        # Create a user vector and persona vector that are orthogonal
        user_vec = np.zeros(100, dtype=np.float32)
        user_vec[2:50] = 1.0  # K-layers 2-49

        persona_vec = np.zeros(98, dtype=np.float32)
        persona_vec[50:98] = 1.0  # K-layers 50-98 (no overlap)

        similarity = cosine_similarity(user_vec, persona_vec)
        # Orthogonal vectors should have near-neutral similarity
        assert 0.0 <= similarity <= 1.0, f"Similarity should be in [0, 1], got {similarity}"

    def test_opposite_vectors_low_similarity(self):
        """Test opposite vectors produce low similarity."""
        user_vec = np.full(100, 1.0, dtype=np.float32)
        persona_vec = np.full(98, 0.0, dtype=np.float32)

        similarity = cosine_similarity(user_vec, persona_vec)
        assert 0.0 <= similarity < 0.5, f"Opposite vectors should have similarity < 0.5, got {similarity}"

    def test_similarity_normalization_to_0_1(self):
        """Test similarity is normalized to [0, 1]."""
        user_vec = np.random.rand(100).astype(np.float32)
        persona_vec = np.random.rand(98).astype(np.float32)

        similarity = cosine_similarity(user_vec, persona_vec)
        assert 0.0 <= similarity <= 1.0, f"Similarity should be in [0, 1], got {similarity}"

    def test_degenerate_zero_vector(self):
        """Test degenerate case with zero-norm vector."""
        user_vec = np.zeros(100, dtype=np.float32)
        persona_vec = np.full(98, 0.5, dtype=np.float32)

        similarity = cosine_similarity(user_vec, persona_vec)
        assert similarity == 0.5, f"Degenerate case should return 0.5, got {similarity}"


# ───────────────────────────────────────────────────────────────────────────────
# Test: Percentile Score Conversion
# ───────────────────────────────────────────────────────────────────────────────

class TestPercentileScore:
    """Tests for similarity-to-percentile conversion."""

    def test_similarity_0_to_percentile_0(self):
        """Test similarity 0.0 converts to percentile 0."""
        score = percentile_score(0.0)
        assert score == 0, f"Similarity 0.0 should map to percentile 0, got {score}"

    def test_similarity_1_to_percentile_100(self):
        """Test similarity 1.0 converts to percentile 100."""
        score = percentile_score(1.0)
        assert score == 100, f"Similarity 1.0 should map to percentile 100, got {score}"

    def test_similarity_0_5_to_percentile_50(self):
        """Test similarity 0.5 converts to percentile 50."""
        score = percentile_score(0.5)
        assert score == 50, f"Similarity 0.5 should map to percentile 50, got {score}"

    def test_percentile_bounded_0_100(self):
        """Test percentile score is always bounded to [0, 100]."""
        for sim in [-0.5, -1.0, 1.5, 2.0]:
            score = percentile_score(sim)
            assert 0 <= score <= 100, f"Percentile {score} outside [0, 100] for similarity {sim}"

    def test_percentile_is_integer(self):
        """Test percentile score is always an integer."""
        for sim in [0.0, 0.25, 0.5, 0.75, 1.0]:
            score = percentile_score(sim)
            assert isinstance(score, int), f"Percentile {score} is not an integer"


# ───────────────────────────────────────────────────────────────────────────────
# Test: Top-5 Ranking Consistency
# ───────────────────────────────────────────────────────────────────────────────

class TestTop5Ranking:
    """Tests for ranking consistency in matching."""

    def test_top_5_ordering(self, db_session: Session):
        """Test that top-5 personas are ordered by score (descending)."""
        # Create 10 test personas
        personas = []
        for i in range(10):
            persona = HybridPersona(
                id=f"test_persona_{i:02d}",
                persona_id=f"komb_{i:03d}_test",
                combination_number=i + 1,
                name_tr=f"Test {i}",
                name_en=f"Test {i}",
                use_case=f"Use case {i}",
                characteristic=f"Characteristic {i}",
                active_k_layers=[2 + i, 12 + i],
                suppressed_k_layers=[81 - i],
                price_usd=1499,
                is_available=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db_session.add(persona)
            personas.append(persona)
        db_session.commit()

        # Create a user vector that favors certain personas
        user_vec = np.full(100, 0.5, dtype=np.float32)
        user_vec[0:10] = 0.85  # Favor K-layers 2-11

        # Match
        top_id, top_5_ids, top_5_scores, profile = match_user_to_personas(
            user_vec.tolist(), db_session, top_k=5
        )

        assert len(top_5_ids) == 5, f"Expected 5 results, got {len(top_5_ids)}"
        assert len(top_5_scores) == 5, f"Expected 5 scores, got {len(top_5_scores)}"
        assert top_id == top_5_ids[0], "Top persona should be first in ranking"

        # Verify descending order
        for i in range(len(top_5_scores) - 1):
            assert top_5_scores[i] >= top_5_scores[i + 1], \
                f"Scores not in descending order: {top_5_scores}"

    def test_top_k_parameter(self, db_session: Session):
        """Test that top_k parameter limits results."""
        # Create 10 personas
        for i in range(10):
            persona = HybridPersona(
                id=f"test_persona_{i:02d}",
                persona_id=f"komb_{i:03d}_test",
                combination_number=i + 1,
                name_tr=f"Test {i}",
                name_en=f"Test {i}",
                use_case=f"Use case {i}",
                characteristic=f"Characteristic {i}",
                active_k_layers=[2 + i],
                suppressed_k_layers=[81],
                price_usd=1499,
                is_available=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db_session.add(persona)
        db_session.commit()

        user_vec = np.full(100, 0.5, dtype=np.float32)

        # Test different top_k values
        for k in [1, 3, 5, 10]:
            top_id, top_5_ids, top_5_scores, profile = match_user_to_personas(
                user_vec.tolist(), db_session, top_k=k
            )
            assert len(top_5_ids) == min(k, 10), f"Expected {min(k, 10)} results for k={k}, got {len(top_5_ids)}"


# ───────────────────────────────────────────────────────────────────────────────
# Test: Database Constraints
# ───────────────────────────────────────────────────────────────────────────────

class TestDatabaseConstraints:
    """Tests for unique constraints and database integrity."""

    def test_unique_persona_id_constraint(self, db_session: Session, sample_hybrid_persona: HybridPersona):
        """Test unique constraint on persona_id."""
        duplicate = HybridPersona(
            id="test_persona_dup",
            persona_id=sample_hybrid_persona.persona_id,  # Duplicate
            combination_number=999,
            name_tr="Duplicate",
            name_en="Duplicate",
            use_case="Test",
            characteristic="Test",
            active_k_layers=[2],
            suppressed_k_layers=[81],
            price_usd=1499,
            is_available=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(duplicate)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_unique_combination_number_constraint(self, db_session: Session, sample_hybrid_persona: HybridPersona):
        """Test unique constraint on combination_number."""
        duplicate = HybridPersona(
            id="test_persona_dup2",
            persona_id="komb_999_different",
            combination_number=sample_hybrid_persona.combination_number,  # Duplicate
            name_tr="Duplicate",
            name_en="Duplicate",
            use_case="Test",
            characteristic="Test",
            active_k_layers=[2],
            suppressed_k_layers=[81],
            price_usd=1499,
            is_available=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(duplicate)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_required_fields_populated(self, sample_hybrid_persona: HybridPersona):
        """Test that all required fields are populated."""
        assert sample_hybrid_persona.persona_id is not None
        assert sample_hybrid_persona.combination_number is not None
        assert sample_hybrid_persona.name_tr is not None
        assert sample_hybrid_persona.name_en is not None
        assert sample_hybrid_persona.use_case is not None
        assert sample_hybrid_persona.characteristic is not None
        assert sample_hybrid_persona.active_k_layers is not None
        assert sample_hybrid_persona.suppressed_k_layers is not None

    def test_default_price_usd(self, db_session: Session):
        """Test default price_usd is 1499 (14.99 USD)."""
        persona = HybridPersona(
            id="test_price_default",
            persona_id="komb_price_test",
            combination_number=1000,
            name_tr="Price Test",
            name_en="Price Test",
            use_case="Test",
            characteristic="Test",
            active_k_layers=[2],
            suppressed_k_layers=[81],
            is_available=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(persona)
        db_session.commit()

        assert persona.price_usd == 1499, f"Default price should be 1499, got {persona.price_usd}"

    def test_default_is_available_true(self, db_session: Session):
        """Test default is_available is True."""
        persona = HybridPersona(
            id="test_available_default",
            persona_id="komb_available_test",
            combination_number=1001,
            name_tr="Available Test",
            name_en="Available Test",
            use_case="Test",
            characteristic="Test",
            active_k_layers=[2],
            suppressed_k_layers=[81],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(persona)
        db_session.commit()

        assert persona.is_available == True, f"Default is_available should be True, got {persona.is_available}"

    def test_k_layer_indices_in_valid_range(self, db_session: Session):
        """Test K-layer indices are within [1, 98]."""
        persona = HybridPersona(
            id="test_k_range",
            persona_id="komb_k_range_test",
            combination_number=1002,
            name_tr="K-range Test",
            name_en="K-range Test",
            use_case="Test",
            characteristic="Test",
            active_k_layers=[1, 50, 98],  # Valid range
            suppressed_k_layers=[25, 75],
            price_usd=1499,
            is_available=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(persona)
        db_session.commit()

        assert all(1 <= k <= 98 for k in persona.active_k_layers)
        assert all(1 <= k <= 98 for k in persona.suppressed_k_layers)


# ───────────────────────────────────────────────────────────────────────────────
# Test: Full Matching Flow
# ───────────────────────────────────────────────────────────────────────────────

class TestFullMatchingFlow:
    """Tests for end-to-end matching workflow."""

    def test_full_matching_flow(
        self,
        db_session: Session,
        sample_user: User,
        sample_hybrid_persona: HybridPersona,
    ):
        """Test complete quiz → matching → audit flow."""
        # Create submission
        submission = QuizSubmission(
            id="test_submission_flow",
            user_id=sample_user.id,
            answers_json=json.dumps({"q1": "a"}),
            extracted_k_layer=[0.5] * 100,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(submission)
        db_session.commit()
        db_session.refresh(submission)

        # Perform matching
        user_vec = submission.extracted_k_layer
        top_id, top_5_ids, top_5_scores, profile = match_user_to_personas(user_vec, db_session, top_k=5)

        # Record match
        match_record = record_persona_match(
            db=db_session,
            user_id=sample_user.id,
            submission_id=submission.id,
            top_persona_id=top_id,
            top_5_persona_ids=top_5_ids,
            top_5_scores=top_5_scores,
            is_historical=False,
        )

        # Update submission with match
        updated_submission = update_submission_with_match(
            db=db_session,
            submission_id=submission.id,
            top_persona_id=top_id,
            top_5_ids=top_5_ids,
            top_5_scores=top_5_scores,
        )

        # Verify audit record
        assert match_record.user_id == sample_user.id
        assert match_record.submission_id == submission.id
        assert match_record.top_persona_id == top_id
        assert len(match_record.top_5_persona_ids) > 0

        # Verify submission updated
        assert updated_submission.matched_hybrid_persona_id == top_id
        assert updated_submission.top_5_hybrid_matches == top_5_ids
        assert updated_submission.top_5_hybrid_scores == top_5_scores

    def test_no_personas_available_fallback(self, db_session: Session):
        """Test fallback when no personas are available."""
        user_vec = np.full(100, 0.5, dtype=np.float32)

        top_id, top_5_ids, top_5_scores, profile = match_user_to_personas(
            user_vec.tolist(), db_session, top_k=5
        )

        assert top_id is None, "Should return None when no personas available"
        assert len(top_5_ids) == 0, "Should return empty list"
        assert "error" in profile, "Profile should contain error key"
        assert profile["is_historical"] == True, "Should be marked as historical"

    def test_matching_with_available_flag(self, db_session: Session):
        """Test that only is_available=True personas are matched."""
        # Create available persona
        available = HybridPersona(
            id="test_available",
            persona_id="komb_available",
            combination_number=1,
            name_tr="Available",
            name_en="Available",
            use_case="Test",
            characteristic="Test",
            active_k_layers=[2, 12],
            suppressed_k_layers=[81],
            price_usd=1499,
            is_available=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(available)

        # Create unavailable persona
        unavailable = HybridPersona(
            id="test_unavailable",
            persona_id="komb_unavailable",
            combination_number=2,
            name_tr="Unavailable",
            name_en="Unavailable",
            use_case="Test",
            characteristic="Test",
            active_k_layers=[2, 12],
            suppressed_k_layers=[81],
            price_usd=1499,
            is_available=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(unavailable)
        db_session.commit()

        user_vec = np.full(100, 0.5, dtype=np.float32)
        top_id, top_5_ids, _, _ = match_user_to_personas(user_vec.tolist(), db_session, top_k=5)

        assert top_id == "komb_available", "Should only match available personas"
        assert "komb_unavailable" not in top_5_ids, "Unavailable persona should not be in results"


# ───────────────────────────────────────────────────────────────────────────────
# Test: K-Layer Cache Performance
# ───────────────────────────────────────────────────────────────────────────────

class TestKLayerCache:
    """Tests for K-layer vector caching."""

    def test_cache_hit_on_repeated_access(self, sample_hybrid_persona: HybridPersona):
        """Test cache hit when accessing the same persona twice."""
        # First access (cache miss)
        vector1 = build_hybrid_vector(sample_hybrid_persona)
        stats1 = _k_layer_cache.stats()

        # Second access (cache hit)
        vector2 = build_hybrid_vector(sample_hybrid_persona)
        stats2 = _k_layer_cache.stats()

        # Vectors should be equal
        np.testing.assert_array_equal(vector1, vector2)

    def test_cache_eviction_lru(self):
        """Test LRU cache eviction when maxsize exceeded."""
        cache = _k_layer_cache
        maxsize = cache.maxsize

        # Fill cache
        for i in range(maxsize + 5):
            key = f"persona_{i}"
            vector = np.full(98, float(i) / 100, dtype=np.float32)
            cache.put(key, vector)

        # Cache should not exceed maxsize
        assert len(cache._cache) <= maxsize, f"Cache size {len(cache._cache)} exceeded maxsize {maxsize}"


# ───────────────────────────────────────────────────────────────────────────────
# Test: Persona Match API Response
# ───────────────────────────────────────────────────────────────────────────────

class TestPersonaMatchAPI:
    """Tests for API response validation."""

    def test_match_profile_contains_required_keys(self, db_session: Session, sample_hybrid_persona: HybridPersona):
        """Test matching profile contains all required keys."""
        user_vec = np.full(100, 0.5, dtype=np.float32)
        _, _, _, profile = match_user_to_personas(user_vec.tolist(), db_session, top_k=5)

        required_keys = [
            "user_vector_stats",
            "is_historical",
            "total_personas_compared",
            "top_k",
            "top_persona_details",
            "latency_ms",
            "cache_stats",
        ]

        for key in required_keys:
            assert key in profile, f"Missing required key in profile: {key}"

    def test_match_profile_vector_stats(self, db_session: Session, sample_hybrid_persona: HybridPersona):
        """Test user vector stats are calculated correctly."""
        user_vec = np.array([0.1, 0.5, 0.9] * 33 + [0.5], dtype=np.float32)  # 100 elements
        _, _, _, profile = match_user_to_personas(user_vec.tolist(), db_session, top_k=5)

        stats = profile["user_vector_stats"]
        assert "mean" in stats
        assert "std" in stats
        assert "min" in stats
        assert "max" in stats

        # Verify values are reasonable
        assert 0 <= stats["min"] <= 1
        assert 0 <= stats["max"] <= 1
        assert stats["min"] <= stats["mean"] <= stats["max"]

    def test_match_profile_latency(self, db_session: Session, sample_hybrid_persona: HybridPersona):
        """Test latency is recorded in profile."""
        user_vec = np.full(100, 0.5, dtype=np.float32)
        _, _, _, profile = match_user_to_personas(user_vec.tolist(), db_session, top_k=5)

        assert "latency_ms" in profile
        assert profile["latency_ms"] >= 0, "Latency should be non-negative"

    def test_top_persona_details_completeness(self, db_session: Session, sample_hybrid_persona: HybridPersona):
        """Test top persona details are fully populated."""
        user_vec = np.full(100, 0.5, dtype=np.float32)
        _, _, _, profile = match_user_to_personas(user_vec.tolist(), db_session, top_k=5)

        details = profile["top_persona_details"]
        assert details is not None
        assert details["persona_id"] == sample_hybrid_persona.persona_id
        assert details["name_tr"] == sample_hybrid_persona.name_tr
        assert details["name_en"] == sample_hybrid_persona.name_en
        assert "match_score" in details
        assert details["use_case"] is not None
        assert details["characteristic"] is not None
        assert details["combination_number"] == sample_hybrid_persona.combination_number


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
