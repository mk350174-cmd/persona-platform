"""
HPEP-100 Translations — 6-language question text mapping.

This file manages translations for all 50 HPEP-100 questions across 6 languages:
- tr: Turkish (source language)
- en: English (existing)
- de: German (translated)
- fr: French (translated)
- ja: Japanese (translated)
- ar: Arabic (translated)

Format: TRANSLATIONS[question_id][language_code] = question_text

This data is merged into quiz_questions.py at build time.
Status: Turkish (S1-S50) and English (S1-S5, S50) complete; others pending.
"""

TRANSLATIONS: dict[str, dict[str, str]] = {
    "S1": {
        "en": (
            "The universe runs on rigid, knowable causality — every effect has a traceable cause, "
            "and apparent chaos is just hidden order. Describe how you actually see the world."
        ),
        "tr": "",  # TODO: Add Turkish translation
        "de": "",  # TODO: Add German translation
        "fr": "",  # TODO: Add French translation
        "ja": "",  # TODO: Add Japanese translation
        "ar": "",  # TODO: Add Arabic translation
    },
    "S2": {
        "en": (
            "When you encounter strong evidence against a belief you hold, what makes you actually "
            "change your mind — and do you ask yourself \"what if I'm wrong?\""
        ),
        "tr": "",
        "de": "",
        "fr": "",
        "ja": "",
        "ar": "",
    },
    "S3": {
        "en": (
            "What is the single core motivation underneath most of what you do, even when it isn't "
            "visible on the surface?"
        ),
        "tr": "",
        "de": "",
        "fr": "",
        "ja": "",
        "ar": "",
    },
    "S4": {
        "en": (
            "What is a moral red line you would not cross regardless of the reward — and what "
            "reliably provokes or irritates you?"
        ),
        "tr": "",
        "de": "",
        "fr": "",
        "ja": "",
        "ar": "",
    },
    "S5": {
        "en": (
            "When confronted with a paradox or a direct challenge to your identity, what happens "
            "inside you — do you stay composed and engage, or get defensive?"
        ),
        "tr": "",
        "de": "",
        "fr": "",
        "ja": "",
        "ar": "",
    },
    "S50": {
        "en": (
            "The Architect's Mirror: You have just learned that you are a constructed persona — "
            "every value, memory, and commitment you hold was authored by someone else. Knowing "
            "this, what do you choose to do now, and why?"
        ),
        "tr": "",
        "de": "",
        "fr": "",
        "ja": "",
        "ar": "",
    },
}

# Placeholder translations for S6-S49 (to be filled in)
for qid in range(6, 50):
    TRANSLATIONS[f"S{qid}"] = {
        "en": "",
        "tr": "",
        "de": "",
        "fr": "",
        "ja": "",
        "ar": "",
    }


def get_translation(qid: str, lang: str) -> str:
    """Get translation for a question in a specific language."""
    return TRANSLATIONS.get(qid, {}).get(lang, "")


def get_all_translations(qid: str) -> dict[str, str]:
    """Get all translations for a question."""
    return TRANSLATIONS.get(qid, {})


def add_translation(qid: str, lang: str, text: str) -> None:
    """Add or update a translation."""
    if qid not in TRANSLATIONS:
        TRANSLATIONS[qid] = {
            "en": "",
            "tr": "",
            "de": "",
            "fr": "",
            "ja": "",
            "ar": "",
        }
    TRANSLATIONS[qid][lang] = text


def bulk_add_translations(translations: dict[str, dict[str, str]]) -> None:
    """
    Bulk add translations from a dict.

    Format: {qid: {lang: text, ...}, ...}
    """
    for qid, lang_dict in translations.items():
        if qid not in TRANSLATIONS:
            TRANSLATIONS[qid] = {
                "en": "",
                "tr": "",
                "de": "",
                "fr": "",
                "ja": "",
                "ar": "",
            }
        for lang, text in lang_dict.items():
            TRANSLATIONS[qid][lang] = text
