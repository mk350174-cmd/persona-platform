"""Tests for HPEP-100 multi-language translations."""

import pytest

from api.quiz_translations import (
    TRANSLATIONS,
    get_translation,
    get_all_translations,
    add_translation,
    bulk_add_translations,
)


def test_translations_structure():
    """Verify translation dict has all required question IDs."""
    assert len(TRANSLATIONS) >= 50
    for qid in [f"S{i}" for i in range(1, 51)]:
        assert qid in TRANSLATIONS
        assert set(TRANSLATIONS[qid].keys()) == {"en", "tr", "de", "fr", "ja", "ar"}


def test_english_translations_complete():
    """Verify S1-S5 and S50 have English translations."""
    for qid in ["S1", "S2", "S3", "S4", "S5", "S50"]:
        assert get_translation(qid, "en")
        assert len(get_translation(qid, "en")) > 10


def test_get_translation():
    """Test get_translation helper."""
    en_text = get_translation("S1", "en")
    assert "causality" in en_text.lower()

    # Turkish not yet available
    tr_text = get_translation("S1", "tr")
    assert tr_text == ""


def test_get_all_translations():
    """Test get_all_translations helper."""
    all_trans = get_all_translations("S1")
    assert set(all_trans.keys()) == {"en", "tr", "de", "fr", "ja", "ar"}
    assert all_trans["en"]
    assert not all_trans["tr"]


def test_add_translation():
    """Test adding individual translations."""
    qid = "S6"
    add_translation(qid, "tr", "Örnek Türkçe soru metni")
    assert get_translation(qid, "tr") == "Örnek Türkçe soru metni"


def test_bulk_add_translations():
    """Test bulk adding translations."""
    new_trans = {
        "S6": {"tr": "Soru 6 Türkçe", "de": "Frage 6 Deutsch"},
        "S7": {"fr": "Question 7 Français"},
    }
    bulk_add_translations(new_trans)

    assert get_translation("S6", "tr") == "Soru 6 Türkçe"
    assert get_translation("S6", "de") == "Frage 6 Deutsch"
    assert get_translation("S7", "fr") == "Question 7 Français"


def test_translation_language_codes():
    """Verify only valid language codes are used."""
    valid_langs = {"en", "tr", "de", "fr", "ja", "ar"}
    for qid, langs in TRANSLATIONS.items():
        assert set(langs.keys()) == valid_langs
