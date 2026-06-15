# Turkish HPEP-100 Integration Log

Tracks the integration of Turkish questions (S1-S50) from source document to production
`api/quiz_questions.py` and `api/quiz_translations.py`.

## Timeline

### Phase 1: Document Reception (Expected June 15, 06:00 UTC)
- **Status**: WAITING
- **Expected**: Turkish Word document (.docx) with 50 HPEP-100 questions
- **Trigger**: File detection in `/home/user/persona-platform/` or monitored directory
- **File pattern**: `*turkish*.docx`, `*HPEP*.docx`, or custom via environment variable

### Phase 2: Parse (Automated)
- **Script**: `scripts/parse_turkish_docx.py`
- **Input**: Word document (.docx)
- **Output**: `turkish_questions_parsed.json`
- **Validation**:
  - Extract all 50 questions (S1-S50)
  - UTF-8 encoding verified
  - File hash computed for integrity
  - Text length validation (no empty questions)
- **Expected duration**: < 5 seconds

### Phase 3: Translate (Automated)
- **Script**: `scripts/translate_to_6langs.py`
- **Input**: `turkish_questions_parsed.json`
- **Output**: `turkish_questions_translated.json`
- **Languages**: tr, en, de, fr, ja, ar (6 total)
- **API**: Gemini 1.5 Flash (free tier, parallel batching)
- **Batch size**: 5 questions per request (respects rate limits)
- **Validation**:
  - K-layer references preserved (K1-K100, CEID, aMCC)
  - Proper nouns unchanged (Bentham, Kant, Lacanian, etc.)
  - Concept preservation verified
- **Expected duration**: 2-3 minutes (with retry/backoff)
- **Fallback**: If API unavailable, parsed file used as-is (Turkish only)

### Phase 4: Integrate (Automated)
- **Script**: `scripts/integrate_quiz_questions.py`
- **Input**: `turkish_questions_translated.json`
- **Operations**:
  1. Update `api/quiz_translations.py` with all 6-language mappings
  2. Update `api/quiz_questions.py` _SPEC table with language dicts
  3. Run full test suite: `pytest tests/test_quiz_*.py`
  4. Validate: All 822+ tests pass, coverage ≥ 89%
- **Rollback instructions**: (see below)
- **Expected duration**: 1-2 minutes (mostly tests)

### Phase 5: Async Monitoring (Running)
- **Script**: `scripts/async_monitor_turkish.py`
- **Behavior**:
  - Polls for file every 1 hour (configurable)
  - Non-blocking, background process
  - Auto-triggers pipeline on file detection (with `--auto-run`)
  - Writes status to `.turkish_monitor_status.json`
  - Logs each phase completion
- **Start command**:
  ```bash
  python scripts/async_monitor_turkish.py --auto-run &
  ```
- **Status file**: `.turkish_monitor_status.json`

---

## Integration Checkpoints

### Parse Checkpoint
- [x] Script created: `scripts/parse_turkish_docx.py`
- [x] Handles .docx extraction
- [x] Validates 50 questions
- [x] Outputs JSON with metadata
- [x] Computes file hash for integrity

### Translate Checkpoint
- [x] Script created: `scripts/translate_to_6langs.py`
- [x] Gemini API integration (free tier)
- [x] Batch processing (5q per request)
- [x] Rate limit handling (exponential backoff)
- [x] Fallback to Turkish-only if API unavailable

### Integrate Checkpoint
- [x] Script created: `scripts/integrate_quiz_questions.py` (existing, enhanced)
- [x] Updates `api/quiz_translations.py`
- [x] Updates `api/quiz_questions.py`
- [x] Runs test suite validation
- [x] Generates integration report

### Monitor Checkpoint
- [x] Script created: `scripts/async_monitor_turkish.py`
- [x] Polls for file arrival
- [x] Auto-triggers pipeline
- [x] Tracks status in JSON
- [x] Non-blocking design

---

## Rollback Instructions

If integration fails at any phase:

### Rollback Phase 4 (Integration)
If tests fail after updating `api/quiz_questions.py` or `api/quiz_translations.py`:

```bash
# Revert to git state
git checkout api/quiz_questions.py api/quiz_translations.py

# Re-run tests to confirm
pytest tests/test_quiz_*.py -v
```

### Rollback Phase 3 (Translation)
If translation output is unusable:

1. Check `GOOGLE_API_KEY` environment variable
2. Re-run translation with `--retry` or increase interval:
   ```bash
   python scripts/translate_to_6langs.py turkish_questions_parsed.json translated_v2.json
   ```
3. If API unavailable, use Turkish-only for now (manual translation later)

### Rollback Phase 2 (Parse)
If parsed output is incomplete or corrupted:

1. Verify `.docx` file integrity (SHA256 hash)
2. Check file format (MS Word 2007+ required)
3. Re-run parse with debug:
   ```bash
   python scripts/parse_turkish_docx.py input.docx output.json --debug
   ```

### Rollback Phase 1 (Reception)
If file arrives corrupted or with wrong encoding:

1. Ask for re-upload with UTF-8 encoding
2. Check file format: must be `.docx` (Word 2007+)
3. Verify question count: exactly 50 (S1-S50)

---

## Monitoring & Status

### Current Status
- **Pipeline**: READY
- **Monitoring**: ACTIVE (checking every 1 hour)
- **File received**: NOT YET
- **Last check**: TBD
- **Integration result**: TBD

### Check Status
```bash
# View monitoring status
cat .turkish_monitor_status.json

# View async monitor logs (if running in background)
ps aux | grep async_monitor_turkish.py

# Check for integration output
ls -lah output/
```

### Manual Trigger
If monitoring doesn't detect file automatically:

```bash
# Parse manually
python scripts/parse_turkish_docx.py hpep100_turkish.docx parsed.json

# Translate manually
python scripts/translate_to_6langs.py parsed.json translated.json

# Integrate manually
python scripts/integrate_quiz_questions.py translated.json
```

---

## Integration Metadata

- **Source repository**: `/home/user/persona-platform/`
- **Target files**:
  - `api/quiz_questions.py` (_SPEC table, QUESTION_BANK)
  - `api/quiz_translations.py` (TRANSLATIONS dict)
- **Test suite**: `tests/test_quiz_*.py` (822 tests)
- **Test coverage target**: ≥ 89%
- **Deployment**: Staging (PR #7 merged to main)

---

## Notes

1. **K-layer mapping**: Questions map to K1-K100 layers. Mappings are already embedded in `api/quiz_questions.py:_SPEC`.
2. **CEID axes**: Each question targets 1-2 CEID axes (C, E, I, D). These are preserved during translation.
3. **Concept preservation**: Gemini is instructed to keep K-layer terminology, proper nouns, and philosophical/psychological tone.
4. **Torch-free**: The integration pipeline runs without PyTorch dependencies (uses json, pathlib, subprocess).
5. **99% confidence**: If all phases succeed, Turkish integration is complete. Manual QA: spot-check 5 random translations + verify test coverage.

---

## HPEP-100 Protocol Reference

- **M8 (Neural_Map)**: Question → K-layer, CEID axes, aMCC engagement
- **M6 (Arkhe)**: Identity continuity scoring
- **M1-M61**: Academic validation papers (61 total)
- **Phase structure**: 10 phases (Root, Cognition, Social, Crisis, Silicon, Time, Language, Ethics, Psychoanalytic, Event Horizon)
- **Total layers**: K1-K100 (0-based in code: K0-K99)
- **Languages**: tr, en, de, fr, ja, ar (6 supported)

---

**Status last updated**: 2026-06-15 00:00 UTC
**Next expected update**: Upon file arrival (2026-06-15 06:00 UTC)
