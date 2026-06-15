# Turkish HPEP-100 Integration Infrastructure

**Status**: FULLY IMPLEMENTED AND READY  
**Date**: June 15, 2026  
**Expected File Arrival**: June 15, 2026 06:00 UTC  
**Infrastructure Ready Since**: June 15, 2026 00:00 UTC  

---

## Overview

Complete zero-touch, automated infrastructure for integrating 50 Turkish HPEP-100 questions into the persona-platform API. The system:

1. **Detects** Turkish Word document arrival (async polling)
2. **Parses** DOCX to JSON (UTF-8, 50 questions S1-S50)
3. **Translates** to 6 languages via Gemini API (tr, en, de, fr, ja, ar)
4. **Integrates** into `api/quiz_questions.py` and `api/quiz_translations.py`
5. **Validates** with full test suite (822+ tests)
6. **Logs** results to `TURKISH_INTEGRATION_LOG.md`

---

## Architecture

```
Turkish Document (.docx)
        ↓
async_monitor_turkish.py [polling every 1 hour]
        ↓ [file detected]
parse_turkish_docx.py
  ├─ Extract 50 questions (S1-S50)
  ├─ Compute file hash
  └─ Output: parsed_turkish.json
        ↓
translate_to_6langs.py
  ├─ Batch API calls to Gemini 1.5 Flash
  ├─ Preserve K-layer terminology
  ├─ Handle rate limits (exponential backoff)
  └─ Output: translated_6langs.json
        ↓
integrate_quiz_questions.py
  ├─ Update api/quiz_translations.py (TRANSLATIONS dict)
  ├─ Update api/quiz_questions.py (_SPEC table)
  ├─ Run pytest tests/test_quiz_*.py
  └─ Output: Updated source files + test report
        ↓
TURKISH_INTEGRATION_LOG.md [appended]
  ├─ Timestamp
  ├─ File metadata
  ├─ Phase results
  └─ Test summary
```

---

## Components

### 1. Parse: `scripts/parse_turkish_docx.py`

**Purpose**: Extract Turkish questions from Word document

**Input**: 
- `hpep100_turkish.docx` (or any `*turkish*.docx` / `*HPEP*.docx`)

**Output**:
- JSON file with:
  - 50 question IDs (S1-S50)
  - Turkish text for each
  - File hash (SHA256) for integrity
  - Parse timestamp (ISO 8601)

**Features**:
- Handles Word 2007+ format (.docx)
- UTF-8 encoding
- Tables and formatted text
- Validates exactly 50 questions

**Usage**:
```bash
python scripts/parse_turkish_docx.py input.docx output.json
```

---

### 2. Translate: `scripts/translate_to_6langs.py`

**Purpose**: Translate Turkish questions to 5 other languages

**Input**: 
- JSON from parse script (Turkish text)

**Output**:
- JSON with 6-language mappings for each question

**API**:
- Gemini 1.5 Flash (free tier)
- Batch size: 5 questions per request
- Rate limit handling: exponential backoff (max 2^30 = 30s wait)

**Features**:
- Preserves K-layer references (K1-K100, CEID, aMCC)
- Preserves proper nouns (Bentham, Kant, etc.)
- Maintains psychological/philosophical tone
- Fallback: If API unavailable, outputs Turkish-only

**Languages**:
- tr (Turkish) — source
- en (English)
- de (German)
- fr (French)
- ja (Japanese)
- ar (Arabic)

**Usage**:
```bash
export GOOGLE_API_KEY="sk-..."
python scripts/translate_to_6langs.py parsed.json translated.json
```

---

### 3. Integrate: `scripts/integrate_quiz_questions.py`

**Purpose**: Merge translations into source code and validate

**Input**:
- JSON with 6-language translations

**Operations**:

1. **Update `api/quiz_translations.py`**
   - Replace TRANSLATIONS dict
   - All 50 questions × 6 languages

2. **Update `api/quiz_questions.py`**
   - Replace _SPEC table
   - Convert `verbatim_text` from string to dict[lang: text]
   - Preserve all metadata (phase, axes, layers, amcc, theme)

3. **Run Tests**
   - `pytest tests/test_quiz_*.py -v`
   - Expects 822+ tests to pass
   - Validates coverage ≥ 89%

4. **Write Log**
   - Append entry to TURKISH_INTEGRATION_LOG.md
   - Record: timestamp, phase results, test summary

**Usage**:
```bash
python scripts/integrate_quiz_questions.py translated.json
```

---

### 4. Monitor: `scripts/async_monitor_turkish.py`

**Purpose**: Async polling for file arrival, auto-trigger pipeline

**Behavior**:
- Polls every 1 hour (configurable via `--interval`)
- Searches for Turkish file patterns:
  - `*turkish*.docx`
  - `*HPEP*.docx`
  - `hpep100_tr.docx`
- On detection: Runs full pipeline (parse → translate → integrate)
- Writes status to `.turkish_monitor_status.json`
- Non-blocking (can run in background)

**Status File** (`.turkish_monitor_status.json`):
```json
{
  "started_at": "2026-06-15T00:00:00Z",
  "file_detected": true,
  "file_path": "./hpep100_turkish.docx",
  "file_hash": "sha256...",
  "pipeline_status": "success",
  "last_check": "2026-06-15T06:15:00Z",
  "checks": 7,
  "pipeline_result": {
    "status": "success",
    "phases": {
      "parse": {"status": "success", "output": "..."},
      "translate": {"status": "success", "output": "..."},
      "integrate": {"status": "success"}
    },
    "duration_seconds": 45.3
  }
}
```

**Usage**:

```bash
# Background monitor (recommended)
python scripts/async_monitor_turkish.py --auto-run --watch-dir . &

# Manual one-time check
python scripts/async_monitor_turkish.py --check-once

# Hourly cron job
0 6 * * * cd /home/user/persona-platform && python scripts/async_monitor_turkish.py --check-once >> /tmp/turkish.log 2>&1
```

---

## Files & Directories

### Core Scripts
- `scripts/parse_turkish_docx.py` (196 lines)
- `scripts/translate_to_6langs.py` (214 lines)
- `scripts/integrate_quiz_questions.py` (268 lines) — **FIXED** (was incomplete)
- `scripts/async_monitor_turkish.py` (338 lines)

### Updated Modules
- `api/quiz_questions.py` — _SPEC table, _normalize_text()
- `api/quiz_translations.py` — TRANSLATIONS dict, get_translation()

### Documentation
- `TURKISH_INTEGRATION_LOG.md` — Integration history (this session + future)
- `TURKISH_INTEGRATION_SETUP.md` — Deployment guide (pre-integration)
- `TURKISH_INTEGRATION_README.md` — This file

### Test Suite
- `tests/test_quiz_units.py` (822+ tests)
- `tests/test_quiz_translations.py`
- `tests/test_quiz_service_extra.py`
- `tests/test_quiz_router.py`

### Status Tracking
- `.turkish_monitor_status.json` — Monitor runtime status

---

## Environment Variables

### Required for Translation Phase
```bash
export GOOGLE_API_KEY="sk-..."  # Gemini free tier API key
```

### Optional
```bash
export PIPELINE_OUTPUT_DIR="/tmp/turkish_integration"  # Default: ./output
```

---

## Deployment Options

### Option 1: Automated Monitor (RECOMMENDED)

Start background monitoring:
```bash
cd /home/user/persona-platform
python scripts/async_monitor_turkish.py --auto-run --watch-dir . &
```

**Benefits**:
- Non-blocking (runs in background)
- Auto-detects file arrival
- Auto-runs full pipeline
- Detailed status tracking

**Check status**:
```bash
cat .turkish_monitor_status.json | python -m json.tool
tail -20 TURKISH_INTEGRATION_LOG.md
```

---

### Option 2: Scheduled Check (Cron)

```bash
# Add to crontab (runs daily at 06:30 UTC)
0 6 * * * cd /home/user/persona-platform && \
  python scripts/async_monitor_turkish.py --check-once >> /tmp/turkish.log 2>&1
```

---

### Option 3: Manual Pipeline

For testing or one-off integration:

```bash
cd /home/user/persona-platform

# Step 1: Parse
python scripts/parse_turkish_docx.py hpep100_turkish.docx /tmp/parsed.json

# Step 2: Translate (requires GOOGLE_API_KEY)
export GOOGLE_API_KEY="sk-..."
python scripts/translate_to_6langs.py /tmp/parsed.json /tmp/translated.json

# Step 3: Integrate
python scripts/integrate_quiz_questions.py /tmp/translated.json

# Step 4: Verify
pytest tests/test_quiz_*.py -v
```

---

## Success Criteria

Integration is **COMPLETE** when:

1. ✓ Turkish file detected (auto or manually placed)
2. ✓ Parse: All 50 questions (S1-S50) extracted
3. ✓ Translate: All 6 languages populated (tr, en, de, fr, ja, ar)
4. ✓ Integrate: `api/quiz_*.py` files updated
5. ✓ Test: All 822+ tests pass
6. ✓ Coverage: ≥ 89%
7. ✓ Log: TURKISH_INTEGRATION_LOG.md updated with "COMPLETE"

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| File not detected | Check filename/location (patterns: `*turkish*.docx`, `*HPEP*.docx`) |
| Parse fails | Verify .docx format (Word 2007+), UTF-8 encoding |
| Translation fails | Set `GOOGLE_API_KEY`, check Gemini free tier quota |
| Tests fail | See rollback plan below, revert changes: `git checkout api/quiz_*.py` |
| Coverage drops | Add tests to `tests/test_quiz_*.py` |

---

## Rollback Instructions

### If Integration Fails (Phase 3)

```bash
# Revert source files
git checkout api/quiz_questions.py api/quiz_translations.py

# Verify tests pass
pytest tests/test_quiz_*.py -v

# Investigate
pytest tests/test_quiz_*.py -v --tb=long
```

### If Translation Fails (Phase 2)

```bash
# Gemini API might be unavailable. Use Turkish-only fallback:
cp /tmp/parsed.json /tmp/translated.json

# Integrate Turkish-only
python scripts/integrate_quiz_questions.py /tmp/parsed.json

# Manual translation can be done later
```

### If Parse Fails (Phase 1)

```bash
# Verify file integrity
sha256sum hpep100_turkish.docx

# Check format (must be Word 2007+)
file hpep100_turkish.docx

# Re-run with debug
python scripts/parse_turkish_docx.py hpep100_turkish.docx /tmp/parsed.json
```

---

## Post-Integration Checklist

Once integration completes successfully:

- [ ] Verify all 822+ tests pass
- [ ] Check coverage ≥ 89%
- [ ] Spot-check 5 random translations (quality)
- [ ] Test API endpoint: `GET /api/quiz/questions?lang=tr`
- [ ] Commit changes: `git add api/quiz_*.py TURKISH_INTEGRATION_LOG.md`
- [ ] Create PR for review and merge to main
- [ ] Deploy to staging/production

---

## Performance Targets

| Phase | Duration | Notes |
|-------|----------|-------|
| Parse | < 5 seconds | Local file processing |
| Translate | 2-3 minutes | Gemini API, 10 batches of 5 questions |
| Integrate | 1-2 minutes | Mostly test execution |
| **Total** | **5-10 minutes** | Full pipeline start to finish |

---

## Key Design Decisions

1. **Async Monitoring**: Non-blocking background process allows for hands-off operation
2. **Batch Translation**: 5 questions per API call respects Gemini free-tier rate limits
3. **Graceful Degradation**: If Gemini unavailable, pipeline uses Turkish-only (fallback)
4. **Test-Driven Integration**: Full test suite validation before committing changes
5. **Status Tracking**: JSON status file for monitoring and debugging
6. **Zero-Dependency**: Integration scripts only use stdlib + documented dependencies

---

## References

### HPEP-100 Protocol
- **M8** (HPEP100_Neural_Map): Question → K-layer, CEID axes, aMCC engagement
- **M6** (Arkhe): Identity continuity scoring
- **M1-M61**: Academic validation papers

### K-Layers & CEID
- **K-layers**: K0-K99 (0-based indexing in code, K1-K100 in docs)
- **CEID Axes**:
  - C = Contextual Consistency
  - E = Epistemic Coherence
  - I = Identity Consistency
  - D = Drift Resistance (moral red lines)

### Test Coverage
- **quiz_questions.py**: Unit tests + integration tests
- **quiz_translations.py**: Language completeness validation
- **quiz_service.py**: End-to-end question + scoring

---

## Contact & Support

For issues or questions about the Turkish integration:

1. Check `.turkish_monitor_status.json` for current status
2. Review `TURKISH_INTEGRATION_LOG.md` for historical records
3. Check `TURKISH_INTEGRATION_SETUP.md` for deployment guide
4. Run troubleshooting commands above

---

## Timeline Summary

| Event | Time (UTC) | Status |
|-------|-----------|--------|
| Infrastructure ready | 2026-06-15 00:00 | ✓ DONE |
| Monitoring starts | 2026-06-15 00:00 | ✓ ACTIVE |
| File expected | 2026-06-15 06:00 | ⏳ WAITING |
| File detected | 2026-06-15 06:05 | 📋 PENDING |
| Parse complete | 2026-06-15 06:10 | 📋 PENDING |
| Translate complete | 2026-06-15 06:20 | 📋 PENDING |
| Integrate complete | 2026-06-15 06:25 | 📋 PENDING |
| Tests pass | 2026-06-15 06:26 | 📋 PENDING |

---

**Last Updated**: 2026-06-15 00:30 UTC  
**Status**: READY FOR DEPLOYMENT  
**Risk Level**: LOW (all scripts tested, dependencies available, rollback planned)
