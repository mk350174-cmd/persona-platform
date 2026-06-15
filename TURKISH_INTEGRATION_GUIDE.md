# Turkish Quiz Integration Guide

## Overview

This guide describes the complete workflow for integrating 50 Turkish HPEP-100 questions into the persona-platform quiz system. The integration spans K-layer alignment, multi-language translation, and schema validation.

**Timeline:** 2-3 hours execution once Turkish questions Word document is received.

---

## Prerequisites

- **Turkish questions file:** Word document (.docx) with 50 questions
- **K-layer mappings:** Reference to HPEP100_Neural_Map (M8 Neurobiological Reference)
- **Dependencies:**
  - `python-docx` (Word document parsing)
  - `google-generativeai` (Gemini API for translations)
  - `pytest` (testing)
  - `pydantic` (schema validation)

Install with:
```bash
pip install python-docx google-generativeai pytest pydantic
export GOOGLE_API_KEY=<your-gemini-api-key>
```

---

## Architecture Overview

```
Turkish Word File
    ↓
[1] parse_turkish_questions.py
    ├─ Extract question text
    ├─ Parse K-layer references (Katman X, Y format)
    ├─ Validate HPEP-100 schema
    └─ Generate Turkish JSON
    ↓
[2] translate_questions_to_6langs.py
    ├─ Use Gemini API for Turkish → {EN, DE, FR, JA, AR}
    ├─ Validate terminology consistency
    ├─ Cache translations to avoid re-work
    └─ Generate 6-language JSON
    ↓
[3] inject_questions_to_quiz.py
    ├─ Merge Turkish questions into quiz_questions.py
    ├─ Update quiz_translations.py with all 6 languages
    ├─ Regenerate public_question_bank()
    ├─ Validate schema integrity
    └─ Back up original files
    ↓
[4] test_turkish_integration.py
    ├─ Verify all 50 questions in database
    ├─ Test all 6 languages accessible
    ├─ Validate K-layer mappings
    ├─ Test CEID axis alignment
    └─ Performance check (<200ms quiz load)
    ↓
[5] TURKISH_QA_CHECKLIST.md
    └─ Manual review & sign-off
```

---

## Step 1: Parse Turkish Word Document

**Script:** `scripts/parse_turkish_questions.py`

### Input Format

The Word document should contain 50 questions in this format:

```
S1: [K-layer references] [CEID axes]
Question text in Turkish...
Theme/category...

S2: ...
...
```

Or with explicit structure:
```
| Question ID | K-layers | CEID | Turkish Text | Theme |
|---|---|---|---|---|
| S1 | K0, K7 | C | Sorular... | Kozmoloji |
```

### K-Layer Reference Format

Parser recognizes these formats:
- `Katman 0, 7` (Turkish: "Layer")
- `K0, K7` (English shorthand)
- `[0, 7]` (JSON array)

### Output

Generates `turkish_questions.json`:
```json
{
  "S1": {
    "text": "Question text in Turkish",
    "layers": [0, 7],
    "ceid": ["C"],
    "phase": 1,
    "theme": "Kozmoloji",
    "amcc": "indirect"
  },
  ...
}
```

### Execution

```bash
python scripts/parse_turkish_questions.py \
  --input questions.docx \
  --output turkish_questions.json \
  --validate
```

**Validation Checks:**
- All 50 questions present (S1-S50)
- K-layer indices 0-99 valid
- CEID axes in {C, E, I, D}
- Phases 1-10 match HPEP-100 spec
- No missing required fields

---

## Step 2: Multi-Language Translation

**Script:** `scripts/translate_questions_to_6langs.py`

### Strategy

Translate Turkish → English, German, French, Japanese, Arabic using Gemini API.

**Key Requirements:**
- **Terminology consistency:** K-layer names, CEID axes, persona terminology preserved
- **Cultural adaptation:** Idiomatic language per locale, not literal
- **Concept preservation:** Scoring rubrics remain equivalent across languages
- **Rate limiting:** 5 questions/batch, 3-retry exponential backoff
- **Caching:** Store translations on-disk to avoid re-work

### Translation Rubric

For each question:
1. Translate Turkish text to 5 target languages
2. Validate each translation preserves:
   - Question intent (not paraphrased)
   - K-layer references (e.g., "Katman 5" → "Layer 5")
   - CEID conceptual boundaries
   - Open-ended format (not multiple choice)
3. Score translation quality: 0-3
   - 0: Fails validation (retry)
   - 1: Acceptable (weak idioms, literal)
   - 2: Good (idiomatic, conceptually accurate)
   - 3: Excellent (native fluency, preserves nuance)

### Language-Specific Notes

- **English:** Finalize any ambiguous phrasing from Turkish
- **German:** Formal "Sie" register, technical terminology
- **French:** Philosophical tradition alignment (Sartre, Derrida references)
- **Japanese:** Kanji compounds for abstract concepts
- **Arabic:** Right-to-left rendering, diacritical marks preserved

### Execution

```bash
python scripts/translate_questions_to_6langs.py \
  --input turkish_questions.json \
  --output translations_6langs.json \
  --validate \
  --batch-size 5 \
  --max-retries 3 \
  --cache-dir .cache/translations
```

**Output:** `translations_6langs.json`
```json
{
  "S1": {
    "tr": "Turkish text...",
    "en": "English text...",
    "de": "Deutscher Text...",
    "fr": "Texte français...",
    "ja": "日本語テキスト...",
    "ar": "النص العربي..."
  },
  ...
}
```

### Gemini API Configuration

The script uses:
- **Model:** `gemini-1.5-flash` (free tier, cost-effective)
- **Rate limit:** 15 req/min (free tier)
- **Batch size:** 5 questions per request
- **Retry:** Exponential backoff (2s → 4s → 8s → 30s max)

Set `GOOGLE_API_KEY`:
```bash
export GOOGLE_API_KEY=<your-key>
```

---

## Step 3: Inject Questions into Quiz System

**Script:** `scripts/inject_questions_to_quiz.py`

### Process

1. **Read translations:** Load `translations_6langs.json`
2. **Parse K-layers:** Extract layer indices from each question
3. **Update quiz_questions.py:**
   - Locate `_SPEC` tuple list
   - Inject Turkish translations as dicts
   - Regenerate QUESTION_BANK
4. **Update quiz_translations.py:**
   - Merge all 6 languages into TRANSLATIONS dict
5. **Validate schema:**
   - All 50 questions present
   - All 6 languages present
   - K-layer indices valid (0-99)
   - CEID axes valid
6. **Back up originals:**
   - `api/quiz_questions.py.backup.<timestamp>`
   - `api/quiz_translations.py.backup.<timestamp>`
7. **Test import:**
   - Verify no syntax errors
   - Import and validate QUESTION_BANK

### Execution

```bash
python scripts/inject_questions_to_quiz.py \
  --input translations_6langs.json \
  --backup \
  --validate
```

### Rollback Procedure

If injection fails or causes errors:

```bash
# List backups
ls -lh api/*.backup.*

# Restore most recent
cp api/quiz_questions.py.backup.<latest> api/quiz_questions.py
cp api/quiz_translations.py.backup.<latest> api/quiz_translations.py

# Verify
python -c "from api.quiz_questions import QUESTION_BANK; print(len(QUESTION_BANK))"
```

---

## Step 4: Integration Testing

**Test Suite:** `tests/test_turkish_integration.py`

### Coverage

1. **Database Integrity**
   - All 50 questions present (S1-S50)
   - No duplicate IDs
   - All required fields populated

2. **Multi-Language Support**
   - All 6 languages accessible via `public_question_bank(lang)`
   - Fallback to English if language unavailable
   - No empty strings in any language

3. **K-Layer Mapping**
   - All layers in range [0, 99]
   - No dangling references
   - Phase assignments match spec (1-10)

4. **CEID Axis Alignment**
   - Axes valid (C, E, I, D only)
   - Axis-to-layer projection correct
   - S50 I-axis scored via NAS

5. **Performance**
   - Quiz load time < 200ms (50 questions)
   - Translation lookup < 50ms
   - Batch translation < 5s for 50 questions

### Execution

```bash
pytest tests/test_turkish_integration.py -v \
  --tb=short \
  --log-cli-level=INFO
```

### Key Test Cases

```python
def test_all_50_questions_present():
    """Verify complete question bank."""
    
def test_all_6_languages_accessible():
    """Verify Turkish + 5 translations available."""
    
def test_k_layer_mappings_valid():
    """Verify all K-layer indices in [0, 99]."""
    
def test_ceid_axis_alignment():
    """Verify CEID axes match layers."""
    
def test_quiz_load_performance():
    """Verify <200ms load time."""
    
def test_language_fallback():
    """Verify English fallback for missing languages."""
```

---

## Step 5: Quality Assurance Checklist

**Manual Review:** `TURKISH_QA_CHECKLIST.md`

Before final sign-off:

- [ ] **Question Comprehension**
  - [ ] All 50 Turkish questions readable
  - [ ] No OCR errors or garbled text
  - [ ] Grammar/spelling checked by native speaker

- [ ] **K-Layer Mapping**
  - [ ] All 50 questions map to valid K-layers
  - [ ] Phase assignments match HPEP-100 spec
  - [ ] amcc (aMCC engagement) values correct

- [ ] **Translation Quality**
  - [ ] All 6 languages present for all 50 questions
  - [ ] Terminology consistent across languages
  - [ ] No machine-generated artifacts
  - [ ] Cultural appropriateness reviewed

- [ ] **Schema Validation**
  - [ ] `quiz_questions.py` imports without errors
  - [ ] `quiz_translations.py` imports without errors
  - [ ] All tests pass (test_turkish_integration.py)

- [ ] **API Verification**
  - [ ] `GET /quiz/questions?lang=tr` returns 50 questions
  - [ ] `GET /quiz/questions?lang=en` returns 50 questions
  - [ ] `GET /quiz/questions?lang=de` returns 50 questions
  - [ ] Languages: fr, ja, ar all work

- [ ] **Documentation**
  - [ ] CLAUDE.md updated with Turkish status
  - [ ] TURKISH_QA_CHECKLIST.md completed
  - [ ] Commit message includes source document reference

---

## Step 6: Deployment Verification

### Pre-Deployment Checks

```bash
# 1. Import validation
python -c "from api.quiz_questions import QUESTION_BANK; print(f'Loaded {len(QUESTION_BANK)} questions')"

# 2. Translation coverage
python -c "from api.quiz_translations import TRANSLATIONS; \
  for lang in ['tr', 'en', 'de', 'fr', 'ja', 'ar']: \
    count = sum(1 for q in TRANSLATIONS.values() if q[lang]); \
    print(f'{lang}: {count}/50')"

# 3. Run integration tests
pytest tests/test_turkish_integration.py -v

# 4. Performance test
time python scripts/benchmark_quiz_load.py
```

### Deployment Steps

1. **Commit changes:**
   ```bash
   git add api/quiz_questions.py api/quiz_translations.py
   git commit -m "feat: Turkish HPEP-100 questions integrated (50 questions, 6 languages)
   
   - Parsed Turkish questions from Word document
   - Translated to EN, DE, FR, JA, AR via Gemini API
   - K-layer mappings validated (0-99)
   - CEID axes aligned with rubrics
   - All 50 questions in public_question_bank()
   - Integration tests passing
   
   References: TURKISH_QA_CHECKLIST.md, TURKISH_INTEGRATION_GUIDE.md"
   ```

2. **Push to feature branch:**
   ```bash
   git push origin claude/bold-bell-u0tvn5
   ```

3. **Create PR with checklist:**
   - Link to TURKISH_QA_CHECKLIST.md
   - Summary: "50 Turkish questions + 6-language translation"
   - Test results attached

4. **Post-deployment validation:**
   ```bash
   # On staging
   curl https://staging-api.persona-platform.io/quiz/questions?lang=tr | jq '.questions | length'
   # Expected: 50
   
   # On production
   curl https://api.persona-platform.io/quiz/questions?lang=tr | jq '.questions | length'
   # Expected: 50
   ```

---

## Troubleshooting

### Common Issues

**Issue:** Gemini API rate limit (429 error)
- **Cause:** Batch size too large or retry limit exceeded
- **Fix:** Reduce batch size to 3, increase max retries to 5
  ```bash
  python scripts/translate_questions_to_6langs.py \
    --batch-size 3 \
    --max-retries 5
  ```

**Issue:** K-layer validation fails
- **Cause:** Invalid layer indices in Word document
- **Fix:** Verify all K-layers in [0, 99], re-parse with validation
  ```bash
  python scripts/parse_turkish_questions.py \
    --input questions.docx \
    --validate \
    --verbose
  ```

**Issue:** Quiz load time > 200ms
- **Cause:** Large translation dict in memory
- **Fix:** Lazy-load translations, cache at module level
  ```python
  # quiz_questions.py
  from functools import lru_cache
  
  @lru_cache(maxsize=128)
  def get_question_text(qid: str, lang: str) -> str:
      return QUESTION_BANK[qid]['text'].get(lang, '')
  ```

**Issue:** Rollback needed
- **Fix:** Restore from backup and re-run validation
  ```bash
  cp api/quiz_questions.py.backup.<timestamp> api/quiz_questions.py
  pytest tests/test_quiz_units.py -v
  ```

---

## Timeline & Estimates

| Phase | Task | Duration | Notes |
|-------|------|----------|-------|
| 1 | Parse Word document | 15 min | Automated |
| 2 | Validate schema | 10 min | Automated |
| 3 | Translate (50 Qs × 6 langs) | 30 min | Gemini API, batched |
| 4 | Validate translations | 15 min | Automated |
| 5 | Inject into quiz system | 10 min | Automated |
| 6 | Run integration tests | 15 min | Automated |
| 7 | Manual QA review | 30 min | Human review |
| 8 | Deployment + post-check | 15 min | Automated + manual |
| **Total** | | **140 min (2h 20m)** | Within 2-3 hour window |

---

## References

- **HPEP-100 Specification:** HPEP100_Neural_Map (M8 Neurobiological Reference)
- **Scoring Rubric:** M8_Arastirma_Paketi (CEID 0-3 scale + NAS)
- **K-Layer Convention:** persona_math/README.md (0-based indices, 100 layers)
- **Gemini API:** https://ai.google.dev/docs (free tier 15 req/min)
- **Multi-Language Support:** api/quiz_translations.py

---

## Future Enhancements

1. **Automatic spelling check** (Turkish + 5 languages)
2. **Back-translation validation** (EN → TR validation)
3. **Phonetic transcription** (Arabic diacritics, Japanese furigana)
4. **Accessibility:** Audio transcription for all 6 languages
5. **A/B testing:** Measure response differences across languages
6. **Regional variants:** PT-BR, ES-ES, etc.

---

**Last Updated:** 2026-06-15  
**Status:** Infrastructure Ready — Awaiting Turkish Word Document  
**Maintainer:** Claude Code Agent
