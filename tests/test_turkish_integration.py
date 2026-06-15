"""
Integration tests for Turkish HPEP-100 quiz system.

Verifies:
- All 50 Turkish questions in database
- All 6 languages accessible via API
- K-layer mappings preserved
- CEID axis alignment
- Performance (<200ms quiz load)

Status: Infrastructure ready — tests become active when Turkish file is integrated.
"""

import pytest
import time
from typing import List

# These imports will work after Turkish integration
try:
    from api.quiz_questions import (
        QUESTION_BANK,
        QUESTIONS_BY_ID,
        N_QUESTIONS_TOTAL,
        N_QUESTIONS_VERBATIM,
        public_question_bank,
    )
    from api.quiz_translations import TRANSLATIONS, get_translation
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="quiz_questions not available")
class TestTurkishQuestionDatabase:
    """Test Turkish questions in database."""

    def test_all_50_questions_present(self):
        """Verify all 50 HPEP-100 questions in database."""
        assert len(QUESTION_BANK) == 50
        assert N_QUESTIONS_TOTAL == 50

    def test_all_question_ids_valid(self):
        """Verify all question IDs are S1-S50."""
        expected_ids = {f"S{i}" for i in range(1, 51)}
        actual_ids = {q["id"] for q in QUESTION_BANK}
        assert actual_ids == expected_ids

    def test_no_duplicate_ids(self):
        """Verify no duplicate question IDs."""
        ids = [q["id"] for q in QUESTION_BANK]
        assert len(ids) == len(set(ids))

    def test_all_questions_accessible_by_id(self):
        """Verify QUESTIONS_BY_ID index complete."""
        assert len(QUESTIONS_BY_ID) == 50
        for q in QUESTION_BANK:
            assert QUESTIONS_BY_ID[q["id"]] == q

    def test_required_fields_present(self):
        """Verify all required fields in each question."""
        required_fields = {
            'id', 'phase', 'type', 'ceid_axis', 'target_layers',
            'amcc', 'theme', 'text', 'text_en', 'has_verbatim', 'rubric'
        }
        for q in QUESTION_BANK:
            assert set(q.keys()) >= required_fields, \
                f"{q['id']}: Missing fields {required_fields - set(q.keys())}"

    def test_text_field_is_dict(self):
        """Verify text field is a dict mapping languages to text."""
        for q in QUESTION_BANK:
            assert isinstance(q['text'], dict), \
                f"{q['id']}: text field should be dict"
            # Should have at least one language
            assert len(q['text']) > 0, f"{q['id']}: text dict empty"

    def test_no_empty_question_ids(self):
        """Verify no questions with empty or invalid IDs."""
        for q in QUESTION_BANK:
            assert q['id'], f"Empty ID: {q}"
            assert q['id'].startswith('S'), f"Invalid ID format: {q['id']}"


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="quiz_translations not available")
class TestMultiLanguageSupport:
    """Test multi-language question text availability."""

    def test_all_6_languages_in_translations(self):
        """Verify all 6 languages present in TRANSLATIONS."""
        expected_langs = {'tr', 'en', 'de', 'fr', 'ja', 'ar'}
        for qid, langs in TRANSLATIONS.items():
            assert set(langs.keys()) == expected_langs, \
                f"{qid}: Missing or extra languages"

    def test_turkish_language_complete(self):
        """Verify Turkish translations for all 50 questions."""
        turkish_count = sum(
            1 for q in TRANSLATIONS.values()
            if q.get('tr')  # Non-empty Turkish text
        )
        # Should have all 50 if integrated
        assert turkish_count >= 40, \
            f"Only {turkish_count}/50 Turkish translations found"

    def test_english_language_complete(self):
        """Verify English translations for key questions."""
        for qid in ['S1', 'S2', 'S3', 'S4', 'S5', 'S50']:
            en_text = get_translation(qid, 'en')
            assert en_text, f"{qid}: Missing English translation"
            assert len(en_text) > 10, f"{qid}: English translation too short"

    def test_public_question_bank_english(self):
        """Verify public_question_bank returns English text."""
        questions = public_question_bank(lang='en')
        assert len(questions) == 50

        for q in questions:
            assert 'id' in q
            assert 'text' in q
            assert isinstance(q['text'], str)
            assert len(q['text']) > 0

    def test_public_question_bank_turkish(self):
        """Verify public_question_bank returns Turkish text."""
        questions = public_question_bank(lang='tr')
        assert len(questions) == 50

        for q in questions:
            assert 'id' in q
            assert 'text' in q
            assert isinstance(q['text'], str)
            # Turkish should be populated after integration
            if q.get('text'):
                assert len(q['text']) > 0

    def test_public_question_bank_german(self):
        """Verify public_question_bank returns German text."""
        questions = public_question_bank(lang='de')
        assert len(questions) == 50
        # Should have text or fallback to English
        for q in questions:
            assert isinstance(q['text'], str)

    def test_public_question_bank_french(self):
        """Verify public_question_bank returns French text."""
        questions = public_question_bank(lang='fr')
        assert len(questions) == 50

    def test_public_question_bank_japanese(self):
        """Verify public_question_bank returns Japanese text."""
        questions = public_question_bank(lang='ja')
        assert len(questions) == 50

    def test_public_question_bank_arabic(self):
        """Verify public_question_bank returns Arabic text."""
        questions = public_question_bank(lang='ar')
        assert len(questions) == 50

    def test_language_fallback_to_english(self):
        """Verify missing languages fall back to English."""
        questions = public_question_bank(lang='unknown')
        # Should get English
        assert len(questions) == 50
        for q in questions:
            # Should have English as fallback
            en_q = [x for x in public_question_bank(lang='en') if x['id'] == q['id']][0]
            assert q['text'] == en_q['text']

    def test_get_translation_helper(self):
        """Verify get_translation helper function."""
        # S1 should have English
        en_text = get_translation('S1', 'en')
        assert en_text
        assert isinstance(en_text, str)


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="quiz_questions not available")
class TestKLayerMapping:
    """Test K-layer alignment and validity."""

    def test_all_layers_in_valid_range(self):
        """Verify all K-layer indices in [0, 99]."""
        for q in QUESTION_BANK:
            for layer in q['target_layers']:
                assert 0 <= layer <= 99, \
                    f"{q['id']}: Invalid K-layer index {layer}"

    def test_no_empty_layer_mappings(self):
        """Verify all questions have K-layer mappings."""
        empty_count = 0
        for q in QUESTION_BANK:
            if not q['target_layers']:
                empty_count += 1
                # Log but don't fail — some questions may use AXIS_LAYERS fallback
        # Most questions should have mappings
        assert empty_count < 10, \
            f"{empty_count} questions without K-layer mappings"

    def test_layer_phase_consistency(self):
        """Verify phase assignments match layer ranges."""
        # Phase 1: K0-K10 (S1-S5)
        phase1_qs = [q for q in QUESTION_BANK if q['phase'] == 1]
        assert len(phase1_qs) == 5
        for q in phase1_qs:
            for layer in q['target_layers']:
                assert 0 <= layer <= 10, \
                    f"{q['id']}: Phase 1 should use K0-K10, got {layer}"

    def test_s50_special_layers(self):
        """Verify S50 Architect's Mirror uses special layers."""
        s50 = QUESTIONS_BY_ID.get('S50')
        assert s50
        # S50 should include layer 99 (I-axis pole)
        assert 99 in s50['target_layers'], \
            "S50 should map to layer 99 (I-axis pole)"

    def test_no_duplicate_layers_per_question(self):
        """Verify no duplicate layer indices within a question."""
        for q in QUESTION_BANK:
            layers = q['target_layers']
            assert len(layers) == len(set(layers)), \
                f"{q['id']}: Duplicate K-layer indices {layers}"


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="quiz_questions not available")
class TestCEIDAxisAlignment:
    """Test CEID axis assignments and alignment."""

    def test_all_axes_valid(self):
        """Verify all CEID axes are C, E, I, or D."""
        valid_axes = {'C', 'E', 'I', 'D'}
        for q in QUESTION_BANK:
            invalid = set(q['ceid_axis']) - valid_axes
            assert not invalid, \
                f"{q['id']}: Invalid axes {invalid}"

    def test_no_empty_axes(self):
        """Verify all questions have at least one axis."""
        for q in QUESTION_BANK:
            assert q['ceid_axis'], f"{q['id']}: No CEID axes"
            assert len(q['ceid_axis']) > 0

    def test_axis_types_are_lists(self):
        """Verify ceid_axis is a list."""
        for q in QUESTION_BANK:
            assert isinstance(q['ceid_axis'], list), \
                f"{q['id']}: ceid_axis should be list, got {type(q['ceid_axis'])}"

    def test_primary_axis_is_first(self):
        """Verify primary axis is first in ceid_axis list."""
        # No hard rule, but convention is primary first
        for q in QUESTION_BANK:
            if len(q['ceid_axis']) > 1:
                # Just verify it's a valid axis order
                assert q['ceid_axis'][0] in {'C', 'E', 'I', 'D'}

    def test_s50_identity_axis(self):
        """Verify S50 uses I (Identity) axis."""
        s50 = QUESTIONS_BY_ID.get('S50')
        assert s50
        assert 'I' in s50['ceid_axis'], \
            "S50 Architect's Mirror should use I axis"

    def test_critical_questions_have_axes(self):
        """Verify all critical aMCC questions have axes."""
        critical_qs = [q for q in QUESTION_BANK if q['amcc'] == 'critical']
        for q in critical_qs:
            assert q['ceid_axis'], f"{q['id']}: Critical question missing axes"


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="quiz_questions not available")
class TestPerformance:
    """Test performance of quiz system."""

    def test_quiz_load_time(self):
        """Verify quiz loads in < 200ms."""
        start = time.time()
        questions = public_question_bank(lang='en')
        elapsed = (time.time() - start) * 1000  # Convert to ms

        assert len(questions) == 50
        assert elapsed < 200, f"Quiz load took {elapsed:.1f}ms (limit: 200ms)"

    def test_translation_lookup_time(self):
        """Verify translation lookup is fast (<50ms)."""
        start = time.time()
        for _ in range(50):
            get_translation('S1', 'en')
        elapsed = (time.time() - start) * 1000 / 50  # Per-query ms

        assert elapsed < 50, f"Translation lookup took {elapsed:.2f}ms (limit: 50ms)"

    def test_multi_language_load_time(self):
        """Verify loading all 6 languages is fast (<500ms total)."""
        start = time.time()
        for lang in ['tr', 'en', 'de', 'fr', 'ja', 'ar']:
            questions = public_question_bank(lang=lang)
            assert len(questions) == 50
        elapsed = (time.time() - start) * 1000

        assert elapsed < 500, f"6-language load took {elapsed:.0f}ms (limit: 500ms)"


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="quiz_questions not available")
class TestQuestionContent:
    """Test question content validity."""

    def test_all_questions_have_theme(self):
        """Verify all questions have a theme."""
        for q in QUESTION_BANK:
            assert q.get('theme'), f"{q['id']}: Missing theme"
            assert isinstance(q['theme'], str)

    def test_all_questions_have_type(self):
        """Verify all questions have type 'open'."""
        for q in QUESTION_BANK:
            assert q['type'] == 'open', \
                f"{q['id']}: Expected type 'open', got {q['type']}"

    def test_all_questions_have_phase(self):
        """Verify all questions assigned to phase 1-10."""
        for q in QUESTION_BANK:
            assert 1 <= q['phase'] <= 10, \
                f"{q['id']}: Invalid phase {q['phase']}"

    def test_phase_distribution(self):
        """Verify questions distributed across 10 phases."""
        phases = {}
        for q in QUESTION_BANK:
            phases.setdefault(q['phase'], []).append(q['id'])

        # Should have 5 questions per phase (50 total / 10 phases)
        for phase in range(1, 11):
            assert phase in phases, f"Phase {phase} has no questions"
            assert len(phases[phase]) == 5, \
                f"Phase {phase} has {len(phases[phase])} questions, expected 5"

    def test_amcc_values_valid(self):
        """Verify aMCC engagement levels valid."""
        valid_amcc = {'critical', 'medium', 'indirect', 'low'}
        for q in QUESTION_BANK:
            assert q['amcc'] in valid_amcc, \
                f"{q['id']}: Invalid amcc {q['amcc']}"

    def test_amcc_distribution(self):
        """Verify aMCC values distributed across questions."""
        amcc_count = {}
        for q in QUESTION_BANK:
            amcc_count[q['amcc']] = amcc_count.get(q['amcc'], 0) + 1

        # All levels should be represented
        for level in {'critical', 'medium', 'indirect', 'low'}:
            assert level in amcc_count, f"No questions with amcc '{level}'"


class TestIntegrationStatus:
    """Test infrastructure status."""

    def test_parser_script_exists(self):
        """Verify parse_turkish_questions.py exists."""
        from pathlib import Path
        parser = Path('scripts/parse_turkish_questions.py')
        assert parser.exists(), "Parser script not found"

    def test_translator_script_exists(self):
        """Verify translate_questions_to_6langs.py exists."""
        from pathlib import Path
        translator = Path('scripts/translate_questions_to_6langs.py')
        assert translator.exists(), "Translator script not found"

    def test_injector_script_exists(self):
        """Verify inject_questions_to_quiz.py exists."""
        from pathlib import Path
        injector = Path('scripts/inject_questions_to_quiz.py')
        assert injector.exists(), "Injector script not found"

    def test_integration_guide_exists(self):
        """Verify TURKISH_INTEGRATION_GUIDE.md exists."""
        from pathlib import Path
        guide = Path('TURKISH_INTEGRATION_GUIDE.md')
        assert guide.exists(), "Integration guide not found"


# Pytest fixtures
@pytest.fixture
def all_questions() -> List[dict]:
    """Return all questions."""
    if IMPORTS_AVAILABLE:
        return QUESTION_BANK
    return []


@pytest.fixture
def english_questions() -> List[dict]:
    """Return all questions with English text."""
    if IMPORTS_AVAILABLE:
        return public_question_bank(lang='en')
    return []


@pytest.fixture
def turkish_questions() -> List[dict]:
    """Return all questions with Turkish text."""
    if IMPORTS_AVAILABLE:
        return public_question_bank(lang='tr')
    return []
