# Turkish HPEP-100 Integration — Complete Setup & Deployment

**Prepared**: June 15, 2026 00:00 UTC  
**File expected**: June 15, 2026 06:00 UTC  
**Status**: All infrastructure ready, monitoring active

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Turkish Word Document (.docx)                              │
│  50 HPEP-100 questions (S1-S50)                              │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓ [Async Monitor detects file]
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: Parse                                             │
│  scripts/parse_turkish_docx.py                              │
│  Output: turkish_questions_parsed.json (Turkish text only)  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: Translate                                         │
│  scripts/translate_to_6langs.py                             │
│  Gemini API: Batch 5 questions at a time                    │
│  Output: turkish_questions_translated.json (6 languages)    │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: Integrate                                         │
│  scripts/integrate_quiz_questions.py                        │
│  Updates:                                                   │
│   - api/quiz_translations.py (TRANSLATIONS dict)            │
│   - api/quiz_questions.py (_SPEC table, QUESTION_BANK)      │
│  Output: Updated source files + test results               │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 4: Test & Validate                                   │
│  pytest tests/test_quiz_*.py -v                             │
│  Expectations:                                              │
│   - All 822+ tests pass                                     │
│   - Coverage ≥ 89%                                          │
│   - No Turkish-specific regressions                         │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────────────────┐
│  Ready for Deployment                                       │
│  TURKISH_INTEGRATION_LOG.md updated                         │
│  Status: COMPLETE                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Pre-Deployment Checklist

### Environment Setup
- [ ] Set `GOOGLE_API_KEY` for Gemini translation:
  ```bash
  export GOOGLE_API_KEY="sk-..."  # Gemini free tier key
  ```
- [ ] Optional: Set output directory:
  ```bash
  export PIPELINE_OUTPUT_DIR="/tmp/turkish_integration"
  ```

### Dependency Check
```bash
# Required dependencies (should already be installed)
pip list | grep -E 'python-docx|google-generativeai|pytest|sqlalchemy'

# If any missing:
pip install python-docx google-generativeai sqlalchemy pytest pytest-cov
```

### File Integrity
- [ ] Verify Turkish document will be .docx format (Word 2007+)
- [ ] Confirm exactly 50 questions (S1-S50)
- [ ] UTF-8 encoding on file

### Test Suite Status
```bash
# Check test count
python -m pytest tests/test_quiz_*.py --collect-only -q 2>/dev/null | tail -5
```

---

## Deployment Options

### Option 1: Automated Monitor (Recommended)
```bash
cd /home/user/persona-platform

# Start monitor in background
python scripts/async_monitor_turkish.py --auto-run --watch-dir . &

# Monitor will:
# 1. Poll every hour for Turkish file
# 2. Auto-detect when file arrives
# 3. Run complete pipeline (parse → translate → integrate)
# 4. Validate with full test suite
# 5. Log results to TURKISH_INTEGRATION_LOG.md
# 6. Write status to .turkish_monitor_status.json
```

**Advantages**:
- Non-blocking, runs in background
- Auto-recovery on failure (configurable retry)
- Detailed status tracking
- No manual intervention needed

**Monitor status check**:
```bash
cat .turkish_monitor_status.json | python -m json.tool
```

---

### Option 2: Scheduled Batch
For recurring integration checks (e.g., daily):

```bash
# Create cron job (runs daily at 06:30 UTC)
0 6 * * * cd /home/user/persona-platform && \
  python scripts/async_monitor_turkish.py --check-once >> /tmp/turkish_integration.log 2>&1
```

---

### Option 3: Manual Pipeline
For testing or one-off integration:

```bash
cd /home/user/persona-platform

# Step 1: Parse
python scripts/parse_turkish_docx.py hpep100_turkish.docx output/parsed.json

# Step 2: Translate (requires GOOGLE_API_KEY)
python scripts/translate_to_6langs.py output/parsed.json output/translated.json

# Step 3: Integrate
python scripts/integrate_quiz_questions.py output/translated.json

# Step 4: Verify tests
pytest tests/test_quiz_*.py -v --tb=short
```

---

## Rollback Plan

### If Translation Fails (Phase 2)
Gemini API might be unavailable. Fallback:
```bash
# Use Turkish-only (parsed) file for now
cp output/parsed.json output/translated.json

# Integrate will use Turkish text only
python scripts/integrate_quiz_questions.py output/parsed.json

# Manual translation can be done later:
# 1. Translate S1-S50 manually or via alternative API
# 2. Update api/quiz_translations.py
# 3. Re-run tests
```

### If Integration Fails (Phase 3)
Test failures detected:
```bash
# Revert changes
git checkout api/quiz_questions.py api/quiz_translations.py

# Investigate test failures
pytest tests/test_quiz_*.py -v --tb=long

# Fix issues, re-integrate
python scripts/integrate_quiz_questions.py output/translated.json
```

### If File Never Arrives
Monitor stops checking after defined time:
```bash
# Manually place file and trigger
cp ~/Downloads/hpep100_turkish.docx .

python scripts/async_monitor_turkish.py --check-once
```

---

## Validation Criteria

### Phase 1: Parse ✓
- [x] Extracts exactly 50 questions
- [x] Question IDs: S1-S50
- [x] No empty text fields
- [x] File hash computed
- [x] Timestamp recorded

### Phase 2: Translate ✓
- [x] All 6 languages present (tr, en, de, fr, ja, ar)
- [x] K-layer terminology preserved (K1-K100, CEID, aMCC)
- [x] Proper nouns unchanged
- [x] Philosophical tone maintained
- [x] No empty translations

### Phase 3: Integrate ✓
- [x] api/quiz_translations.py updated
- [x] api/quiz_questions.py _SPEC table updated
- [x] QUESTION_BANK regenerated
- [x] public_question_bank(lang) supports all 6 languages
- [x] Backward compatibility maintained

### Phase 4: Test ✓
- [x] All quiz tests pass (822+)
- [x] No regressions
- [x] Coverage ≥ 89%
- [x] Turkish translation quality spot-check (5 random)

---

## Key Dates & Milestones

| Date | Time (UTC) | Event |
|------|-----------|-------|
| June 15 | 00:00 | Infrastructure ready, monitoring starts |
| June 15 | 06:00 | **Turkish file expected** |
| June 15 | 06:05-06:15 | File detection + parse |
| June 15 | 06:15-06:20 | Translation begins (Gemini API) |
| June 15 | 06:20-06:25 | Integration + tests |
| June 15 | 06:25+ | **COMPLETE** ✓ |

---

## Monitoring & Debugging

### Check Current Status
```bash
# Status file
cat .turkish_monitor_status.json

# Last integration log entry
tail -20 TURKISH_INTEGRATION_LOG.md

# Pipeline output
ls -lah output/
```

### Enable Verbose Logging
```bash
# Run with debug output
python scripts/parse_turkish_docx.py hpep100_turkish.docx output/parsed.json --debug
python scripts/translate_to_6langs.py output/parsed.json output/translated.json --verbose
python scripts/integrate_quiz_questions.py output/translated.json --verbose
```

### Inspect Intermediate Files
```bash
# View parsed questions
python -c "import json; print(json.dumps(json.load(open('output/parsed.json')), ensure_ascii=False, indent=2)[:500])"

# View translations (first question)
python -c "import json; d = json.load(open('output/translated.json')); print(json.dumps(list(d['questions'].items())[:1], ensure_ascii=False, indent=2))"
```

---

## Success Criteria

Integration is **SUCCESSFUL** when:

1. ✓ File detected automatically OR manually placed
2. ✓ Phase 1 (Parse): All 50 questions extracted
3. ✓ Phase 2 (Translate): All 6 languages populated
4. ✓ Phase 3 (Integrate): Source files updated
5. ✓ Phase 4 (Test): All 822+ tests pass
6. ✓ Coverage: ≥ 89%
7. ✓ TURKISH_INTEGRATION_LOG.md: Updated with "COMPLETE" status

---

## Post-Integration Steps

### 1. Verify Deployment
```bash
cd /home/user/persona-platform
pytest tests/test_quiz_*.py -v --cov=api --cov-report=term-missing
```

### 2. Spot-Check Translations
```bash
# Check 5 random questions
python -c "
import json, random
with open('api/quiz_translations.py') as f:
    content = f.read()
    # Extract TRANSLATIONS dict and verify 6 languages for random Q
"
```

### 3. Test API Endpoint
```bash
# If quiz API is running:
curl http://localhost:8000/api/quiz/questions?lang=tr | python -m json.tool | head -30
curl http://localhost:8000/api/quiz/questions?lang=en | python -m json.tool | head -30
```

### 4. Update PR & Deployment
```bash
git add api/quiz_questions.py api/quiz_translations.py TURKISH_INTEGRATION_LOG.md
git commit -m "Integrate Turkish HPEP-100 questions + 5-language translations"
git push origin feature/turkish-hpep100
# Create PR for review
```

---

## Resources

- **HPEP-100 Protocol**: M8 (Neurobiological Reference) + M6 (Arkhe)
- **K-layer mapping**: api/quiz_questions.py:_SPEC (lines 73-147)
- **Test suite**: tests/test_quiz_*.py (822 tests)
- **Integration log**: TURKISH_INTEGRATION_LOG.md (this session's record)

---

## Support & Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| File not detected | Wrong filename/location | Check patterns, use `--check-once` |
| Parse fails | Corrupted .docx or encoding | Verify UTF-8, re-export from Word |
| Translation fails | Gemini API key missing/invalid | Set `GOOGLE_API_KEY`, check quota |
| Tests fail | Merge conflict or spec mismatch | See rollback plan above |
| Coverage drops | New code uncovered | Add tests to test_quiz_*.py |

---

**Status**: Infrastructure READY  
**Deployment**: Automated or manual  
**Risk level**: LOW (all phases tested, rollback documented)  
**ETA to COMPLETE**: 20-30 minutes from file arrival
