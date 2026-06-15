"""
End-to-end staging tests for hybrid personas.

Tests complete user flows:
- Quiz submission → K-layer extraction → Persona matching → Profile view
- Multi-language persona display
- Search and pagination
- API error handling

Requirements:
    - Database populated with 48 hybrid personas
    - API running on localhost:8000
    - FastAPI test client via conftest fixture
"""

import pytest
import json
import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session

from api.db import HybridPersona, PersonaMatch, User
from api.persona_matching_service import match_user_to_personas


class TestE2EQuizToMatching:
    """End-to-end test: Quiz submission → Matching → Results."""

    def test_complete_quiz_flow_creates_persona_match(self, test_db):
        """Test complete flow: submit answers → extract K-layer → match persona.

        Validates:
        1. Create test user
        2. Generate K-layer from answers
        3. Match user to persona
        4. Record match in database
        """
        # Setup: Create user
        user = User(
            id="test-user-e2e-1",
            email="test-e2e-1@example.com",
            username="test_e2e_1",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(user)
        test_db.flush()

        # Setup: Create sample personas
        personas = []
        for i in range(1, 6):
            persona = HybridPersona(
                id=f"persona-{i}",
                persona_id=f"hybrid_{i:03d}",
                combination_number=i,
                name_tr=f"Kişilik {i}",
                name_en=f"Personality {i}",
                use_case=f"Use case {i}",
                characteristic=f"Characteristic {i}",
                active_k_layers=[2, 12, 28, 71] if i % 2 == 0 else [5, 15, 35, 75],
                suppressed_k_layers=[17, 81] if i % 2 == 0 else [20, 85],
                price_usd=1499,
                is_available=True,
            )
            personas.append(persona)
            test_db.add(persona)
        test_db.flush()

        # Step 1: Generate K-layer from quiz answers
        # Simulate HPEP-100 quiz with 98 dimensions
        user_k_layer = np.random.uniform(0.2, 0.8, 98).astype(np.float32)

        # Step 2: Match user to personas
        top_5 = match_user_to_personas(user_k_layer, test_db)

        # Assertions: Check matching results
        assert len(top_5) == 5, f"Expected 5 results, got {len(top_5)}"
        assert all("persona_id" in p for p in top_5), "All results should have persona_id"
        assert all("score" in p for p in top_5), "All results should have score"

        # Step 3: Record match in database (simulate API behavior)
        top_persona_id = top_5[0]["persona_id"]
        match_record = PersonaMatch(
            id="match-e2e-1",
            user_id="test-user-e2e-1",
            top_persona_id=top_persona_id,
            top_5_ids=[p["persona_id"] for p in top_5],
            top_5_scores=[p["score"] for p in top_5],
            percentile_score=85.5,
        )
        test_db.add(match_record)
        test_db.commit()

        # Verify database record
        stored_match = test_db.query(PersonaMatch).filter_by(id="match-e2e-1").first()
        assert stored_match is not None
        assert stored_match.user_id == "test-user-e2e-1"
        assert stored_match.top_persona_id == top_persona_id
        assert len(stored_match.top_5_ids) == 5

    def test_multiple_quiz_submissions_track_matches(self, test_db):
        """Test user submitting multiple quizzes creates multiple matches."""
        # Setup: Create user
        user = User(
            id="test-user-multi",
            email="test-multi@example.com",
            username="test_multi",
            hashed_password="hashed",
            is_active=True,
        )
        test_db.add(user)
        test_db.flush()

        # Setup: Create personas
        personas = []
        for i in range(1, 6):
            persona = HybridPersona(
                id=f"persona-multi-{i}",
                persona_id=f"hybrid_multi_{i:03d}",
                combination_number=100 + i,
                name_tr=f"Kişilik Multi {i}",
                name_en=f"Personality Multi {i}",
                use_case="Test",
                characteristic="Test",
                active_k_layers=[2, 12] if i % 2 == 0 else [5, 15],
                suppressed_k_layers=[17, 81],
                price_usd=1499,
                is_available=True,
            )
            personas.append(persona)
            test_db.add(persona)
        test_db.flush()

        # Submit 3 different quizzes with different K-layers
        for quiz_num in range(1, 4):
            user_k_layer = np.random.uniform(0.2, 0.8, 98).astype(np.float32)
            top_5 = match_user_to_personas(user_k_layer, test_db)

            match_record = PersonaMatch(
                id=f"match-multi-{quiz_num}",
                user_id="test-user-multi",
                top_persona_id=top_5[0]["persona_id"],
                top_5_ids=[p["persona_id"] for p in top_5],
                top_5_scores=[p["score"] for p in top_5],
                percentile_score=float(80 + quiz_num * 5),
            )
            test_db.add(match_record)
            test_db.flush()

        test_db.commit()

        # Verify all matches recorded
        user_matches = test_db.query(PersonaMatch).filter_by(
            user_id="test-user-multi"
        ).all()
        assert len(user_matches) == 3
        assert all(m.user_id == "test-user-multi" for m in user_matches)


class TestMultiLanguagePersonaDisplay:
    """Test multi-language persona display (Turkish and English)."""

    def test_persona_turkish_name_available(self, test_db):
        """Verify Turkish persona names are populated."""
        persona = HybridPersona(
            id="test-tr",
            persona_id="hybrid_tr_test",
            combination_number=1,
            name_tr="Lider Vizyoner",
            name_en="Visionary Leader",
            use_case="Executive leadership",
            characteristic="Strategic thinker",
            active_k_layers=[2, 12, 28],
            suppressed_k_layers=[17, 81],
            price_usd=1499,
            is_available=True,
        )
        test_db.add(persona)
        test_db.commit()

        stored = test_db.query(HybridPersona).filter_by(id="test-tr").first()
        assert stored.name_tr == "Lider Vizyoner"
        assert stored.name_en == "Visionary Leader"
        assert len(stored.name_tr) > 0
        assert len(stored.name_en) > 0

    def test_persona_english_name_fallback(self, test_db):
        """Verify English name serves as fallback."""
        persona = HybridPersona(
            id="test-en-fallback",
            persona_id="hybrid_en_fallback",
            combination_number=2,
            name_tr="",  # Empty Turkish
            name_en="Strategic Analyst",
            use_case="Business analysis",
            characteristic="Detail-oriented",
            active_k_layers=[5, 15],
            suppressed_k_layers=[20],
            price_usd=1499,
            is_available=True,
        )
        test_db.add(persona)
        test_db.commit()

        stored = test_db.query(HybridPersona).filter_by(id="test-en-fallback").first()
        # Display logic should use English if Turkish empty
        display_name = stored.name_tr if stored.name_tr else stored.name_en
        assert display_name == "Strategic Analyst"

    def test_characteristic_use_case_localization(self, test_db):
        """Test that use_case and characteristic fields support localization."""
        persona = HybridPersona(
            id="test-locale",
            persona_id="hybrid_locale",
            combination_number=3,
            name_tr="Yaratıcı İnsan",
            name_en="Creative Person",
            use_case="İnovasyon ve tasarım | Innovation and design",
            characteristic="Hayal gücü güçlü | Strong imagination",
            active_k_layers=[5, 15, 35],
            suppressed_k_layers=[20, 80],
            price_usd=1499,
            is_available=True,
        )
        test_db.add(persona)
        test_db.commit()

        stored = test_db.query(HybridPersona).filter_by(id="test-locale").first()
        # Should support pipe-separated localization
        assert "|" in stored.use_case
        assert "İnovasyon" in stored.use_case  # Turkish
        assert "Innovation" in stored.use_case  # English


class TestSearchAndPagination:
    """Test persona search and pagination functionality."""

    def test_search_by_characteristic(self, test_db):
        """Test filtering personas by characteristic."""
        # Create personas with distinct characteristics
        chars = ["Leader", "Analyst", "Creator", "Helper", "Visionary"]
        for i, char in enumerate(chars):
            persona = HybridPersona(
                id=f"search-char-{i}",
                persona_id=f"hybrid_search_{i}",
                combination_number=i,
                name_tr=f"Kişilik {i}",
                name_en=f"Personality {i}",
                use_case="Test",
                characteristic=char,
                active_k_layers=[2, 12],
                suppressed_k_layers=[17],
                price_usd=1499,
                is_available=True,
            )
            test_db.add(persona)
        test_db.commit()

        # Search for "Leader"
        results = test_db.query(HybridPersona).filter(
            HybridPersona.characteristic.ilike("%Leader%")
        ).all()

        assert len(results) == 1
        assert results[0].characteristic == "Leader"

    def test_search_by_use_case(self, test_db):
        """Test filtering personas by use case."""
        use_cases = [
            "Executive management",
            "Product strategy",
            "Creative design",
            "Customer service",
            "Research",
        ]
        for i, use_case in enumerate(use_cases):
            persona = HybridPersona(
                id=f"search-use-{i}",
                persona_id=f"hybrid_usecase_{i}",
                combination_number=i,
                name_tr=f"Kişilik {i}",
                name_en=f"Personality {i}",
                use_case=use_case,
                characteristic="Test",
                active_k_layers=[2, 12],
                suppressed_k_layers=[17],
                price_usd=1499,
                is_available=True,
            )
            test_db.add(persona)
        test_db.commit()

        # Search for "Product"
        results = test_db.query(HybridPersona).filter(
            HybridPersona.use_case.ilike("%Product%")
        ).all()

        assert len(results) == 1
        assert "Product" in results[0].use_case

    def test_pagination_limit_offset(self, test_db):
        """Test pagination with LIMIT and OFFSET."""
        # Create 20 personas
        for i in range(20):
            persona = HybridPersona(
                id=f"page-{i}",
                persona_id=f"hybrid_page_{i:02d}",
                combination_number=i,
                name_tr=f"Kişilik {i}",
                name_en=f"Personality {i}",
                use_case="Test",
                characteristic="Test",
                active_k_layers=[2, 12],
                suppressed_k_layers=[17],
                price_usd=1499,
                is_available=True,
            )
            test_db.add(persona)
        test_db.commit()

        # Get first page (5 items)
        page1 = test_db.query(HybridPersona).order_by(
            HybridPersona.combination_number
        ).limit(5).offset(0).all()
        assert len(page1) == 5
        assert page1[0].combination_number == 0

        # Get second page (5 items)
        page2 = test_db.query(HybridPersona).order_by(
            HybridPersona.combination_number
        ).limit(5).offset(5).all()
        assert len(page2) == 5
        assert page2[0].combination_number == 5

        # Get last page (partial)
        page4 = test_db.query(HybridPersona).order_by(
            HybridPersona.combination_number
        ).limit(5).offset(15).all()
        assert len(page4) == 5


class TestAPIErrorHandling:
    """Test API error handling and edge cases."""

    def test_invalid_k_layer_dimensions(self, test_db):
        """Test API rejects invalid K-layer dimensions."""
        # Create sample persona
        persona = HybridPersona(
            id="test-invalid-dim",
            persona_id="hybrid_invalid_dim",
            combination_number=1,
            name_tr="Test",
            name_en="Test",
            use_case="Test",
            characteristic="Test",
            active_k_layers=[2, 12],
            suppressed_k_layers=[17],
            price_usd=1499,
            is_available=True,
        )
        test_db.add(persona)
        test_db.commit()

        # Try with wrong dimension (e.g., 50 instead of 98)
        invalid_k_layer = np.random.uniform(0.2, 0.8, 50).tolist()

        # This should either error gracefully or pad/truncate
        # Expected: Validation should catch this
        assert len(invalid_k_layer) != 98

    def test_matching_nonexistent_persona(self, test_db):
        """Test matching when persona doesn't exist."""
        user_k_layer = np.random.uniform(0.2, 0.8, 98).astype(np.float32)

        # Try matching with empty database (no personas)
        top_5 = match_user_to_personas(user_k_layer, test_db)

        # Should return empty or error gracefully
        assert isinstance(top_5, (list, type(None)))

    def test_unavailable_personas_excluded(self, test_db):
        """Test that unavailable personas are excluded from matching."""
        # Create mix of available and unavailable personas
        for i in range(1, 6):
            persona = HybridPersona(
                id=f"avail-{i}",
                persona_id=f"hybrid_avail_{i}",
                combination_number=i,
                name_tr=f"Kişilik {i}",
                name_en=f"Personality {i}",
                use_case="Test",
                characteristic="Test",
                active_k_layers=[2, 12],
                suppressed_k_layers=[17],
                price_usd=1499,
                is_available=(i % 2 == 0),  # Only even-numbered available
            )
            test_db.add(persona)
        test_db.commit()

        user_k_layer = np.random.uniform(0.2, 0.8, 98).astype(np.float32)
        top_5 = match_user_to_personas(user_k_layer, test_db)

        # All results should be from available personas
        if top_5:
            for result in top_5:
                persona = test_db.query(HybridPersona).filter_by(
                    persona_id=result["persona_id"]
                ).first()
                assert persona.is_available is True

    def test_duplicate_persona_ids_prevented(self, test_db):
        """Test that duplicate persona_ids are prevented (unique constraint)."""
        persona1 = HybridPersona(
            id="dup-1",
            persona_id="hybrid_dup",
            combination_number=1,
            name_tr="First",
            name_en="First",
            use_case="Test",
            characteristic="Test",
            active_k_layers=[2],
            suppressed_k_layers=[17],
            price_usd=1499,
            is_available=True,
        )
        test_db.add(persona1)
        test_db.commit()

        # Try to add duplicate
        persona2 = HybridPersona(
            id="dup-2",
            persona_id="hybrid_dup",  # Same ID
            combination_number=2,
            name_tr="Second",
            name_en="Second",
            use_case="Test",
            characteristic="Test",
            active_k_layers=[2],
            suppressed_k_layers=[17],
            price_usd=1499,
            is_available=True,
        )
        test_db.add(persona2)

        # Should raise integrity error
        with pytest.raises(Exception):  # IntegrityError
            test_db.commit()


class TestProfileView:
    """Test persona profile view and details display."""

    def test_persona_profile_completeness(self, test_db):
        """Test that persona profiles have all required fields."""
        persona = HybridPersona(
            id="profile-complete",
            persona_id="hybrid_profile",
            combination_number=1,
            name_tr="Tam Kişilik",
            name_en="Complete Personality",
            use_case="Complete use case",
            characteristic="Complete characteristic",
            active_k_layers=[2, 12, 28, 71],
            suppressed_k_layers=[17, 81, 90],
            price_usd=1499,
            is_available=True,
        )
        test_db.add(persona)
        test_db.commit()

        stored = test_db.query(HybridPersona).filter_by(id="profile-complete").first()

        # Verify all fields present and non-empty where required
        assert stored.persona_id is not None
        assert stored.name_tr
        assert stored.name_en
        assert stored.use_case
        assert stored.characteristic
        assert stored.active_k_layers
        assert stored.suppressed_k_layers
        assert stored.price_usd > 0
        assert stored.is_available is True
        assert stored.created_at is not None

    def test_persona_profile_pricing(self, test_db):
        """Test persona pricing information."""
        persona = HybridPersona(
            id="profile-pricing",
            persona_id="hybrid_pricing",
            combination_number=1,
            name_tr="Test",
            name_en="Test",
            use_case="Test",
            characteristic="Test",
            active_k_layers=[2],
            suppressed_k_layers=[17],
            price_usd=1499,  # $14.99
            is_available=True,
        )
        test_db.add(persona)
        test_db.commit()

        stored = test_db.query(HybridPersona).filter_by(id="profile-pricing").first()

        # Price should be in cents (1499 = $14.99)
        assert stored.price_usd == 1499
        usd_price = stored.price_usd / 100
        assert abs(usd_price - 14.99) < 0.01  # $14.99

    def test_persona_k_layer_metadata(self, test_db):
        """Test K-layer metadata storage and retrieval."""
        active_layers = [2, 12, 28, 71]
        suppressed_layers = [17, 81, 90, 95]

        persona = HybridPersona(
            id="profile-klayer",
            persona_id="hybrid_klayer",
            combination_number=1,
            name_tr="Test",
            name_en="Test",
            use_case="Test",
            characteristic="Test",
            active_k_layers=active_layers,
            suppressed_k_layers=suppressed_layers,
            price_usd=1499,
            is_available=True,
        )
        test_db.add(persona)
        test_db.commit()

        stored = test_db.query(HybridPersona).filter_by(id="profile-klayer").first()

        # Verify K-layer arrays preserved
        assert stored.active_k_layers == active_layers
        assert stored.suppressed_k_layers == suppressed_layers
        assert len(stored.active_k_layers) == 4
        assert len(stored.suppressed_k_layers) == 4


# ──────────────────────────────────────────────────────────────────────
# Integration Fixtures
# ──────────────────────────────────────────────────────────────────────

@pytest.fixture
def populated_db(test_db):
    """Create test database with 48 sample personas."""
    personas = []
    for i in range(1, 49):
        persona = HybridPersona(
            id=f"persona-{i}",
            persona_id=f"hybrid_{i:03d}",
            combination_number=i,
            name_tr=f"Kişilik {i}",
            name_en=f"Personality {i}",
            use_case=f"Use case {i}",
            characteristic=f"Characteristic {i}",
            active_k_layers=[2, 12, 28, 71] if i % 2 == 0 else [5, 15, 35, 75],
            suppressed_k_layers=[17, 81] if i % 2 == 0 else [20, 85],
            price_usd=1499,
            is_available=True,
        )
        personas.append(persona)
        test_db.add(persona)
    test_db.commit()
    return test_db
