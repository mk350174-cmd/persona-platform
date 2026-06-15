# Turkish HPEP-100 Integration — Quick Start

**Status**: Ready for production  
**Date**: June 15, 2026  
**Expected file arrival**: June 15, 06:00 UTC

---

## Pre-Checklist (Before File Arrives)

Run these commands to verify the system is ready:

```bash
# 1. Verify all scripts exist
ls -la scripts/{parse_turkish_docx,translate_to_6langs,integrate_quiz_questions,async_monitor_turkish}.py
# Expected: 4 files found

# 2. Verify dependencies installed
pip list | grep -E "python-docx|google-generativeai"
# Expected: python-docx and google-generativeai listed

# 3. Verify test suite ready
pytest tests/test_quiz_*.py --collect-only | head -20
# Expected: 822+ tests collected

# 4. Set Gemini API key (required for translation)
export GOOGLE_API_KEY=<your-free-tier-api-key>
echo $GOOGLE_API_KEY | wc -c  # Should be ~39 characters
# Get key at: https://aistudio.google.com/app/apikey
```

---

## When File Arrives (June 15, 06:00 UTC)

### Automatic Mode (Recommended)

```bash
# Start the async monitor
python scripts/async_monitor_turkish.py --auto-run &

# Monitor will automatically:
# 1. Detect the Turkish .docx file
# 2. Parse it (extract 50 questions)
# 3. Translate to 6 languages
# 4. Integrate into api/quiz_questions.py
# 5. Run 822+ tests
# 6. Update TURKISH_INTEGRATION_LOG.md

# Check status
cat .turkish_monitor_status.json
```

**Duration**: ~5 minutes total  
**Expected output**: "pipeline_status": "success"

### Manual Mode

If you have the file ready now:

```bash
# Step 1: Parse the Turkish Word document
python scripts/parse_turkish_docx.py hpep100_turkish.docx output/parsed.json
# Output: output/parsed.json (with 50 questions)

# Step 2: Translate to 6 languages (requires GOOGLE_API_KEY)
python scripts/translate_to_6langs.py output/parsed.json output/translated.json
# Output: output/translated.json (6-language translations)

# Step 3: Integrate and validate
python scripts/integrate_quiz_questions.py output/translated.json
# Output: Updated api/quiz_questions.py, api/quiz_translations.py, test report
```

---

## Post-Integration Validation

After pipeline completes, verify success:

```bash
# 1. Check pipeline status
cat .turkish_monitor_status.json | jq '.pipeline_status'
# Expected: "success"

# 2. Verify all 50 questions in system
python -c "from api.quiz_questions import _SPEC; print(f'Questions: {len(_SPEC)}')"
# Expected: Questions: 50

# 3. Verify all 6 languages present
python -c "
from api.quiz_translations import TRANSLATIONS
sample_qid = 'S1'
langs = list(TRANSLATIONS[sample_qid].keys())
print(f'{sample_qid} languages: {langs}')
"
# Expected: S1 languages: ['tr', 'en', 'de', 'fr', 'ja', 'ar']

# 4. Run quiz tests
pytest tests/test_quiz_*.py -v --tb=short
# Expected: 822+ tests passed, ≥89% coverage
```

---

## Troubleshooting (If Something Fails)

### Monitor Not Starting

```bash
# Verify Python version (3.8+)
python --version

# Verify monitor can find file
python scripts/async_monitor_turkish.py --check-once

# If still stuck, check for errors
python scripts/async_monitor_turkish.py --watch-dir . --check-once 2>&1 | head -30
```

### Parse Failed (Stage 1)

```bash
# Verify file exists and is .docx
file hpep100_turkish.docx

# Verify file is not corrupted
python -c "from docx import Document; doc = Document('hpep100_turkish.docx'); print(f'Paragraphs: {len(doc.paragraphs)}')"

# If error, ask for re-upload with UTF-8 encoding
```

### Translation API Failed (Stage 2)

```bash
# Verify API key
echo $GOOGLE_API_KEY

# Check if key is valid
python -c "import google.generativeai as genai; genai.configure(api_key='$GOOGLE_API_KEY'); print('✓ API key valid')"

# If rate-limited (error 429), wait 30 minutes and retry
# Gemini free tier: 60 requests/min, 1500 requests/day
```

### Integration/Tests Failed (Stage 3)

```bash
# Check which test failed
pytest tests/test_quiz_*.py -v --tb=short | grep FAILED

# If new questions broke existing tests, check test_quiz_service_extra.py
# May need to update test mocks for new K-layer projections

# Run with more detail
pytest tests/test_quiz_router.py::TestQuizEndpoints -vv
```

---

## Rollback (If Integration Breaks Existing Code)

```bash
# Revert all changes to API files
git checkout api/quiz_questions.py api/quiz_translations.py

# Verify tests pass again
pytest tests/test_quiz_*.py -v

# Identify what broke in integration output
cat .turkish_monitor_status.json | jq '.pipeline_result.phases.integrate.error'
```

---

## Key Files & Locations

| Purpose | File | Status |
|---------|------|--------|
| Parse script | `scripts/parse_turkish_docx.py` | ✓ Ready |
| Translate script | `scripts/translate_to_6langs.py` | ✓ Ready |
| Integrate script | `scripts/integrate_quiz_questions.py` | ✓ Ready |
| Monitor script | `scripts/async_monitor_turkish.py` | ✓ Ready |
| Question bank (target) | `api/quiz_questions.py` | ✓ Ready |
| Translations (target) | `api/quiz_translations.py` | ✓ Ready |
| Test suite | `tests/test_quiz_*.py` | ✓ Ready (4 files) |
| Integration guide | `TURKISH_INFRASTRUCTURE_GUIDE.md` | ✓ Ready |
| Integration log | `TURKISH_INTEGRATION_LOG.md` | ✓ Ready |
| Monitor status | `.turkish_monitor_status.json` | Auto-created |

---

## Expected Success Criteria

✓ **Parse**: 50 questions extracted (S1-S50)  
✓ **Translate**: 6-language JSON with all questions  
✓ **Integrate**: api/quiz_questions.py updated with language dicts  
✓ **Test**: ≥822 tests passed, ≥89% coverage  
✓ **Production**: New questions available via `/api/quiz/question/{qid}?lang=<lang>`

---

## API Usage (After Integration)

Once integrated, the Turkish questions are available via:

```bash
# Get question in Turkish
curl "http://localhost:8000/api/quiz/question/S1?lang=tr"

# Get question in English
curl "http://localhost:8000/api/quiz/question/S1?lang=en"

# Get question in other languages
curl "http://localhost:8000/api/quiz/question/S1?lang=de"   # German
curl "http://localhost:8000/api/quiz/question/S1?lang=fr"   # French
curl "http://localhost:8000/api/quiz/question/S1?lang=ja"   # Japanese
curl "http://localhost:8000/api/quiz/question/S1?lang=ar"   # Arabic
```

---

## Support Resources

1. **Full documentation**: `TURKISH_INFRASTRUCTURE_GUIDE.md`
2. **Integration history**: `TURKISH_INTEGRATION_LOG.md`
3. **Question mapping**: `api/quiz_questions.py:_SPEC`
4. **Scoring rubric**: `api/quiz_questions.py:AXIS_RUBRIC`

---

**Status**: 🟢 READY  
**Last Check**: June 15, 2026  
**Next Step**: Await Turkish file arrival or trigger manual integration
