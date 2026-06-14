# HPEP-100 Turkish Integration Guide

**Status:** Ready for Turkish questions upload  
**Date:** June 14, 2026  
**Branch:** `claude/bold-bell-u0tvn5`  

---

## Overview

The HPEP-100 quiz infrastructure is fully prepared for multi-language support (TR, EN, DE, FR, JA, AR). This document outlines the exact steps to integrate Turkish questions once the Word document is received.

---

## Current State (✅ Ready)

### Completed Infrastructure
- ✅ `api/quiz_questions.py` — Multi-language dict-based text support
- ✅ `api/routers/quiz.py` — Language parameter on GET /questions endpoint
- ✅ `api/quiz_translations.py` — Translation management system
- ✅ `api/quiz_service.py` — Persona extraction scoring engine
- ✅ `tests/test_quiz_router.py` — 35+ integration tests
- ✅ `tests/test_quiz_translations.py` — Translation system tests
- ✅ Coverage: **89.19%** (822/822 tests passing)

### English Questions Status
- S1-S5: ✅ Complete with K-layer mappings
- S6-S49: ⏳ Pending Turkish source → will auto-generate English translations
- S50: ✅ Complete

---

## Integration Steps (When File Arrives)

### Phase 1: Parse Turkish Questions (15 min)
**Input:** Word document with 50 Turkish HPEP-100 questions  
**Output:** JSON mapping (S1-S50) with Turkish text and K-layer info

```
S1: {
  "tr": "Evrene, insan ilişkilerine ... [Turkish text from Word]",
  "k_layers": [0, 7],  # Extract from Word or reference spec
  "ceid_axes": ["C"]   # From M8_HPEP100_v2.tex
}
...
```

**Action:**
1. Extract text from Word → JSON parser
2. Verify all 50 questions present (S1-S50)
3. Cross-reference K-layer mapping with `api/quiz_questions.py` _SPEC
4. Flag any discrepancies in `papers/M8_HPEP100_v2.tex`

### Phase 2: Translate Turkish → 5 Languages (1 hour)
**Input:** JSON with 50 Turkish questions  
**Output:** Dict-based text field with all 6 languages

**Translation Strategy (Parallel Gemini API):**
```python
# Pseudo-code for translation
for qid in ["S1", "S2", ..., "S50"]:
    turkish_text = parsed_json[qid]["tr"]
    for lang in ["en", "de", "fr", "ja", "ar"]:
        translated = gemini_translate(
            text=turkish_text,
            source_lang="tr",
            target_lang=lang,
            context="HPEP-100 Persona Extraction Protocol"
        )
        translations[qid][lang] = translated
```

**Quality Checks:**
- No K-layer concepts lost in translation
- Phase/type consistency maintained
- Language-specific idioms handled correctly

### Phase 3: Integrate into quiz_questions.py (30 min)
**Location:** `api/quiz_questions.py` lines 15-170 (_SPEC definition)

**Current Structure (Single Language):**
```python
_SPEC: list[tuple] = [
    ("S1", 1, ["C"], [0, 7], "indirect", "Cosmology", "The universe runs on rigid..."),
    ...
]
```

**New Structure (6 Languages):**
```python
_SPEC: list[tuple] = [
    ("S1", 1, ["C"], [0, 7], "indirect", "Cosmology", {
        "tr": "Evrene, insan ilişkilerine ... [from Word]",
        "en": "The universe runs on rigid ... [existing or translated]",
        "de": "Das Universum läuft auf starrer ...",
        "fr": "L'univers fonctionne sur une causalité ...",
        "ja": "宇宙は厳格で知ることのできる因果関係で動いています...",
        "ar": "يعمل الكون على السببية الصارمة القابلة للمعرفة...",
    }),
    ...
]
```

**Modifications:**
1. Update `_SPEC` tuple element [6] from `str` → `dict[str, str]`
2. Ensure `_normalize_text()` handles new dict format (already does ✅)
3. Update `QUESTION_BANK` building to store dict (already does ✅)
4. No changes needed to `public_question_bank(lang)` function ✅

### Phase 4: Test & Validate (15 min)

**Run Full Test Suite:**
```bash
cd /home/user/persona-platform
pytest tests/ --cov=api --cov-report=term-missing --cov-fail-under=80 -v
```

**Expected Results:**
- ✅ 822+ tests passing
- ✅ 80%+ coverage (target: 89%+)
- ✅ Language parameter validation works for all 6 langs
- ✅ Quiz submission handles Turkish answers correctly

**Specific Language Tests:**
```bash
# Test each language individually
curl "http://localhost:8000/api/v1/quiz/questions?lang=tr" | jq '.[0]'
curl "http://localhost:8000/api/v1/quiz/questions?lang=ja" | jq '.[0]'
# ... and so on for de, fr, ar
```

**Persona Extraction Test:**
```python
# POST /api/v1/quiz/submit with sample answers
# Should extract K-layer + CEID scores regardless of question language
```

### Phase 5: Commit & Push (5 min)

```bash
git add api/quiz_questions.py api/quiz_translations.py
git commit -m "feat: integrate Turkish HPEP-100 questions + 5-language translations

- Added 50 Turkish questions from Word document
- Translated to EN, DE, FR, JA, AR via Gemini
- Updated quiz_questions.py with multi-language dict support
- All 822 tests passing with 89%+ coverage

https://claude.ai/code/session_<SESSION_ID>"

git push -u origin claude/bold-bell-u0tvn5
```

---

## File Locations & Responsibilities

| File | Role | Status |
|------|------|--------|
| `api/quiz_questions.py` | Main QUESTION_BANK with _SPEC | Ready for Turkish integration |
| `api/routers/quiz.py` | API endpoints (lang param) | ✅ Complete |
| `api/quiz_translations.py` | Translation storage | Ready for bulk import |
| `api/quiz_service.py` | Persona extraction | ✅ Complete |
| `tests/test_quiz_*.py` | Integration & unit tests | ✅ All passing (35+ tests) |
| `papers/M8_HPEP100_v2.tex` | K-layer specification reference | ✅ Reference only |

---

## Troubleshooting Checklist

| Issue | Check | Fix |
|-------|-------|-----|
| Test fails on Turkish text | UTF-8 encoding in Word file | Ensure file saved as UTF-8 .docx |
| Language parameter rejected | Invalid language code | Must be: tr, en, de, fr, ja, ar (exact case) |
| K-layer mismatch | Question number vs. mapping | Cross-reference with _SPEC target_layers |
| Coverage drops | New code not tested | Run full test suite; may need new test case |
| Persona extraction fails | Missing K-layer data in translation | Verify translation preserves concept integ… |

---

## Quick Reference: Language Codes

| Code | Language | Status |
|------|----------|--------|
| `tr` | Turkish | ⏳ Pending Word document |
| `en` | English | ✅ Existing (S1-S5, S50) |
| `de` | German | Ready for Gemini translation |
| `fr` | French | Ready for Gemini translation |
| `ja` | Japanese | Ready for Gemini translation |
| `ar` | Arabic | Ready for Gemini translation |

---

## API Endpoints (Post-Integration)

### Get Questions in Turkish
```bash
GET /api/v1/quiz/questions?lang=tr
Response: [
  {
    "id": "S1",
    "phase": 1,
    "type": "open",
    "text": "Evrene, insan ilişkilerine ... [Turkish]"
  },
  ...
]
```

### Submit Quiz (Multi-Language Agnostic)
```bash
POST /api/v1/quiz/submit
Headers: X-API-Key: <your_api_key>
Body: {
  "answers": {
    "S1": 0.5,
    "S2": 0.7,
    ...
  }
}
Response: {
  "persona": {
    "k_layer": [0.45, 0.52, ...],
    "ceid_scores": {"C": 0.6, "E": 0.5, ...},
    "created_at": "2026-06-14T23:30:00Z"
  },
  "checkout_url": "/checkout/hpep100?..."
}
```

---

## Timeline Estimate

| Phase | Duration | Blocker |
|-------|----------|---------|
| **1. Parse Turkish** | 15 min | Word file |
| **2. Translate (Gemini)** | 1 hour | Turkish + Gemini API |
| **3. Integrate code** | 30 min | Parsed data |
| **4. Test & validate** | 15 min | None |
| **5. Commit & push** | 5 min | None |
| **Total** | **2 hours** | Step 1 |

---

## Next Steps (After Integration)

1. ✅ PR #7 merge (pending: Turkish integration)
2. ⏳ Deploy quiz to staging environment
3. ⏳ Create React Quiz UI page (`frontend/src/pages/Quiz.jsx`)
4. ⏳ Add checkout flow for $5 HPEP-100 SKU
5. ⏳ User testing with multi-language support
6. ⏳ Production deployment

---

## Reference Files

- **Specification:** `papers/M8_HPEP100_v2.tex`
- **Code:** `api/quiz_questions.py`, `api/routers/quiz.py`, `api/quiz_service.py`
- **Tests:** `tests/test_quiz_router.py`, `tests/test_quiz_translations.py`
- **Status:** `HPEP100_STATUS.md`

---

**Last Updated:** 2026-06-14  
**Prepared By:** Claude Code  
**Ready:** ✅ Awaiting Turkish questions Word document
