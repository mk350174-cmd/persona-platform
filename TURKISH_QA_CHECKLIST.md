# Turkish HPEP-100 Integration — QA Checklist

> **PROCESS NOT YET EXECUTED (audit finding AF-P-005, 2026-07-29):**
> this checklist is entirely blank. No QA review has occurred; do not
> treat this document as evidence of QA sign-off.

**Integration Date:** ________________
**Integrator:** ________________  
**Reviewer:** ________________  

---

## Phase 1: Pre-Integration Validation

### Word Document Quality
- [ ] File format: .docx (Word document)
- [ ] File size: Reasonable (<10 MB)
- [ ] All 50 questions present (S1-S50)
- [ ] No corrupted text or encoding issues
- [ ] Readable in Microsoft Word, LibreOffice, Google Docs

### Turkish Text Review
- [ ] **Spelling Check:** All questions spell-checked by native Turkish speaker
- [ ] **Grammar:** All questions grammatically correct
- [ ] **Clarity:** Questions are clear and unambiguous
- [ ] **Terminology:** Consistent use of Turkish terminology across all 50 questions
- [ ] **No OCR Artifacts:** No garbled text, special characters correctly rendered
- [ ] **UTF-8 Encoding:** Turkish diacritics (ş, ğ, ı, ö, ü, ç) correctly encoded

### K-Layer Mapping Review
- [ ] **Coverage:** All 50 questions map to valid K-layers
- [ ] **Valid Indices:** All K-layer indices in range [0, 99]
- [ ] **No Duplicates:** No duplicate layers within a question
- [ ] **Phase Alignment:** Layer assignments match HPEP-100 phase structure
  - [ ] Phase 1 (S1-S5): Kök ve Çekirdek (K0-K10)
  - [ ] Phase 2 (S6-S10): Bilişsel İşleme (K11-K20)
  - [ ] Phase 3 (S11-S15): Sosyal Dinamikler (K21-K30)
  - [ ] Phase 4 (S16-S20): Kriz Yönetimi (K31-K40)
  - [ ] Phase 5 (S21-S25): Silikon Mimarisi (K41-K50)
  - [ ] Phase 6 (S26-S30): Zaman & Tarihsellik (K51-K60)
  - [ ] Phase 7 (S31-S35): Dilbilimsel Oyunlar (K61-K70)
  - [ ] Phase 8 (S36-S40): Etik Yargı (K71-K80)
  - [ ] Phase 9 (S41-S45): Psikanalitik Varlık (K81-K90)
  - [ ] Phase 10 (S46-S50): Olay Ufku (K91-K100)

### CEID Axis Mapping Review
- [ ] **All Axes Valid:** Only C, E, I, D used
- [ ] **No Empty Axes:** Every question has at least one axis
- [ ] **Alignment with Semantics:**
  - [ ] C (Context) axis assigned to contextual/cosmological questions
  - [ ] E (Epistemic) axis assigned to knowledge/evidence questions
  - [ ] I (Identity) axis assigned to self/continuity questions
  - [ ] D (Drift) axis assigned to moral/commitment questions
- [ ] **Primary Axis First:** Primary axis listed first in each question

### aMCC Engagement Levels
- [ ] **Valid Levels:** Only critical, medium, indirect, low used
- [ ] **Appropriate Classification:**
  - [ ] Critical questions (17-20 expected): High brain engagement, key differentiators
  - [ ] Medium questions (10-15 expected): Moderate complexity
  - [ ] Indirect questions (10-15 expected): Lower engagement
  - [ ] Low questions (5-10 expected): Baseline/exploratory

---

## Phase 2: Parsing Validation

### Parse Script Execution
```bash
python scripts/parse_turkish_questions.py \
  --input questions.docx \
  --output turkish_questions.json \
  --validate
```

- [ ] Script runs without errors
- [ ] No import errors (python-docx available)
- [ ] Output JSON file created: `turkish_questions.json`
- [ ] JSON is valid (can be opened in text editor)
- [ ] All 50 questions in JSON output

### JSON Structure Validation
- [ ] Each question has required fields:
  - [ ] `id` (S1-S50)
  - [ ] `text` (Turkish text)
  - [ ] `layers` (list of K-layer indices)
  - [ ] `ceid` (list of axes)
  - [ ] `phase` (1-10)
  - [ ] `theme` (question theme)
  - [ ] `amcc` (engagement level)

### Data Integrity Checks
- [ ] All 50 questions present in JSON
- [ ] No missing required fields
- [ ] All K-layer indices valid (0-99)
- [ ] All CEID axes valid (C, E, I, D only)
- [ ] All phases valid (1-10)
- [ ] All aMCC levels valid (critical, medium, indirect, low)

---

## Phase 3: Translation Validation

### Translation Script Execution
```bash
export GOOGLE_API_KEY=<your-key>
python scripts/translate_questions_to_6langs.py \
  --input turkish_questions.json \
  --output translations_6langs.json \
  --validate \
  --batch-size 5
```

- [ ] Gemini API key configured (GOOGLE_API_KEY set)
- [ ] Script runs without errors
- [ ] No rate limiting issues (or retries work)
- [ ] Output JSON file created: `translations_6langs.json`
- [ ] Translation completes in reasonable time (~15-20 minutes)

### Translation Coverage
- [ ] All 50 questions translated
- [ ] All 6 languages present for each question (tr, en, de, fr, ja, ar)
- [ ] No empty translations
- [ ] All language fields contain text

### Translation Quality Review

**English (EN)** — Native speaker review
- [ ] [ ] Terminology consistent
- [ ] [ ] Phrasing natural and idiomatic
- [ ] [ ] K-layer references preserved
- [ ] [ ] No grammatical errors
- [ ] [ ] Open-ended format maintained

**German (DE)** — Native speaker review (or fluent reviewer)
- [ ] [ ] Formal "Sie" register used appropriately
- [ ] [ ] Technical terminology correct
- [ ] [ ] No literal translations (idiomatic preferred)
- [ ] [ ] K-layer terminology (Schicht/Layer) consistent

**French (FR)** — Native speaker review
- [ ] [ ] Philosophical tone appropriate
- [ ] [ ] References to French tradition (Sartre, Derrida) culturally apt
- [ ] [ ] No awkward phrasing
- [ ] [ ] Accent marks/diacritics correct

**Japanese (JA)** — Native speaker review
- [ ] [ ] Kanji compounds appropriate
- [ ] [ ] Hiragana/Katakana usage correct
- [ ] [ ] Abstract concepts properly conveyed
- [ ] [ ] No furigana needed (or added correctly)

**Arabic (AR)** — Native speaker review
- [ ] [ ] Right-to-left text rendering verified
- [ ] [ ] Diacritical marks (tashkeel) present where needed
- [ ] [ ] Modern Standard Arabic (MSA) or Egyptian Arabic consistent
- [ ] [ ] No gender/number agreement issues

### Concept Preservation Checks
- [ ] K-layer references preserved across all languages
- [ ] CEID axes unchanged (C, E, I, D not translated)
- [ ] Question intent consistent across translations
- [ ] Scoring rubric equivalence maintained
- [ ] No paraphrasing (faithful translation)
- [ ] Cultural context appropriate for each locale

---

## Phase 4: Injection Validation

### Injection Script Execution
```bash
python scripts/inject_questions_to_quiz.py \
  --input translations_6langs.json \
  --backup \
  --validate
```

- [ ] Script runs without errors
- [ ] Backup files created:
  - [ ] `api/quiz_questions.py.backup.<timestamp>`
  - [ ] `api/quiz_translations.py.backup.<timestamp>`
- [ ] No syntax errors in updated files
- [ ] Files successfully validated

### Schema Integrity

**quiz_questions.py**
- [ ] All 50 questions in QUESTION_BANK
- [ ] QUESTIONS_BY_ID index complete
- [ ] N_QUESTIONS_TOTAL = 50
- [ ] N_QUESTIONS_VERBATIM >= 50
- [ ] All required fields present

**quiz_translations.py**
- [ ] TRANSLATIONS dict created
- [ ] All 50 questions in TRANSLATIONS
- [ ] All 6 languages in each question
- [ ] No empty translations (except where appropriate)

### Import Validation
```bash
python -c "from api.quiz_questions import QUESTION_BANK; print(len(QUESTION_BANK))"
python -c "from api.quiz_translations import TRANSLATIONS; print(len(TRANSLATIONS))"
```

- [ ] quiz_questions.py imports without errors
- [ ] quiz_translations.py imports without errors
- [ ] QUESTION_BANK accessible
- [ ] TRANSLATIONS accessible
- [ ] Helper functions work (`public_question_bank`, `get_translation`)

---

## Phase 5: Integration Testing

### Test Suite Execution
```bash
pytest tests/test_turkish_integration.py -v --tb=short
```

- [ ] All tests pass
- [ ] 50 questions present
- [ ] All 6 languages accessible
- [ ] K-layer mappings valid
- [ ] CEID axes aligned
- [ ] Performance < 200ms

### Individual Test Groups

**Database Integrity**
- [ ] `test_all_50_questions_present` ✓
- [ ] `test_all_question_ids_valid` ✓
- [ ] `test_no_duplicate_ids` ✓
- [ ] `test_required_fields_present` ✓

**Multi-Language Support**
- [ ] `test_all_6_languages_in_translations` ✓
- [ ] `test_turkish_language_complete` ✓
- [ ] `test_english_language_complete` ✓
- [ ] `test_public_question_bank_*` (all 6 langs) ✓
- [ ] `test_language_fallback_to_english` ✓

**K-Layer Mapping**
- [ ] `test_all_layers_in_valid_range` ✓
- [ ] `test_layer_phase_consistency` ✓
- [ ] `test_s50_special_layers` ✓

**CEID Axis Alignment**
- [ ] `test_all_axes_valid` ✓
- [ ] `test_no_empty_axes` ✓
- [ ] `test_s50_identity_axis` ✓

**Performance**
- [ ] `test_quiz_load_time` ✓ (< 200ms)
- [ ] `test_translation_lookup_time` ✓ (< 50ms)
- [ ] `test_multi_language_load_time` ✓ (< 500ms)

---

## Phase 6: API Verification

### Quiz Endpoint Testing

**English (lang=en)**
```bash
curl -X GET "http://localhost:8000/quiz/questions?lang=en" \
  -H "Accept: application/json"
```
- [ ] Returns 200 OK
- [ ] Returns exactly 50 questions
- [ ] All questions have English text
- [ ] All fields populated

**Turkish (lang=tr)**
```bash
curl -X GET "http://localhost:8000/quiz/questions?lang=tr" \
  -H "Accept: application/json"
```
- [ ] Returns 200 OK
- [ ] Returns exactly 50 questions
- [ ] All questions have Turkish text
- [ ] No English fallback required

**German (lang=de)**
- [ ] Returns 200 OK
- [ ] 50 questions with German text

**French (lang=fr)**
- [ ] Returns 200 OK
- [ ] 50 questions with French text

**Japanese (lang=ja)**
- [ ] Returns 200 OK
- [ ] 50 questions with Japanese text

**Arabic (lang=ar)**
- [ ] Returns 200 OK
- [ ] 50 questions with Arabic text

### Language Fallback Testing

**Unknown language (lang=unknown)**
```bash
curl -X GET "http://localhost:8000/quiz/questions?lang=unknown" \
  -H "Accept: application/json"
```
- [ ] Falls back to English
- [ ] Returns 50 questions
- [ ] All questions have English text

**Missing language parameter (no lang)**
- [ ] Defaults to English
- [ ] Returns 50 questions

---

## Phase 7: Content Review & Sign-Off

### Native Speaker Reviews (Assign to Team)

**Turkish (TR) — Reviewed by: _______________**
- [ ] All 50 questions readable and appropriate
- [ ] No OCR or encoding errors
- [ ] Terminology consistent with HPEP-100 tradition
- [ ] Cultural context appropriate for Turkey
- [ ] Comments/notes:
  ```
  
  
  ```
- [ ] **APPROVED** ☐  **NEEDS FIXES** ☐

**English (EN) — Reviewed by: _______________**
- [ ] All translations accurate
- [ ] Terminology aligned with psychological/philosophical tradition
- [ ] No paraphrasing or meaning loss
- [ ] Idiomatic and natural-sounding
- [ ] Comments/notes:
  ```
  
  
  ```
- [ ] **APPROVED** ☐  **NEEDS FIXES** ☐

**German (DE) — Reviewed by: _______________**
- [ ] Formal register appropriate
- [ ] Technical terminology correct
- [ ] Idiomatic phrasing
- [ ] Comments/notes:
  ```
  
  
  ```
- [ ] **APPROVED** ☐  **NEEDS FIXES** ☐

**French (FR) — Reviewed by: _______________**
- [ ] Philosophical tone maintained
- [ ] Cultural references appropriate
- [ ] Natural expression
- [ ] Comments/notes:
  ```
  
  
  ```
- [ ] **APPROVED** ☐  **NEEDS FIXES** ☐

**Japanese (JA) — Reviewed by: _______________**
- [ ] Kanji/Hiragana usage appropriate
- [ ] Abstract concepts properly conveyed
- [ ] Cultural context
- [ ] Comments/notes:
  ```
  
  
  ```
- [ ] **APPROVED** ☐  **NEEDS FIXES** ☐

**Arabic (AR) — Reviewed by: _______________**
- [ ] Right-to-left rendering verified
- [ ] Diacritics correct
- [ ] Modern Standard Arabic (or preferred dialect) consistent
- [ ] Comments/notes:
  ```
  
  
  ```
- [ ] **APPROVED** ☐  **NEEDS FIXES** ☐

---

## Phase 8: Final Sign-Off

### Integration Manager Checklist
- [ ] All parsing validation complete
- [ ] All translation quality reviews complete
- [ ] All injection tests passing
- [ ] All API endpoints verified
- [ ] All native speaker reviews approved
- [ ] No blocking issues or regressions

### Deployment Authorization
- [ ] Code reviewed by architecture team
- [ ] No breaking changes to existing API
- [ ] Backward compatibility verified
- [ ] Documentation updated
- [ ] Release notes prepared

### Sign-Off

**Integration Manager:** _______________  
**Date:** _______________  
**Status:** ☐ **APPROVED FOR DEPLOYMENT**  ☐ **NEEDS REVISION**

**Approving Director:** _______________  
**Date:** _______________  
**Authorization:** ☐ **APPROVED**  ☐ **CONDITIONAL**  ☐ **DEFERRED**

---

## Post-Deployment Verification (48 hours)

### Production Monitoring
- [ ] Quiz endpoint responding normally
- [ ] All 6 languages working in production
- [ ] Performance metrics within SLA (<200ms)
- [ ] No error rate increase
- [ ] User feedback collected

### Monitoring Queries
```sql
-- Check question access by language
SELECT lang, COUNT(*) as access_count 
FROM quiz_logs 
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY lang;

-- Check API response times
SELECT AVG(response_time_ms) 
FROM api_metrics 
WHERE endpoint = '/quiz/questions'
  AND timestamp > NOW() - INTERVAL '24 hours';
```

- [ ] All languages being used
- [ ] Response times healthy
- [ ] Error rates normal

---

## Rollback Plan (If Needed)

**Rollback Procedure:**
```bash
# Restore from backup
cp api/quiz_questions.py.backup.<timestamp> api/quiz_questions.py
cp api/quiz_translations.py.backup.<timestamp> api/quiz_translations.py

# Verify restoration
pytest tests/test_quiz_units.py -v

# Redeploy
git reset --hard HEAD~1
```

- [ ] Backup files preserved in secure location
- [ ] Rollback procedure documented and tested
- [ ] Communication plan for rollback readiness

---

## Lessons Learned & Future Improvements

### What Went Well
```


```

### What Could Improve
```


```

### Recommendations for Next Integration
```


```

---

**Document Completed By:** _______________  
**Date:** _______________  
**Revision:** 1.0  
**Status:** ✓ SIGNED OFF
