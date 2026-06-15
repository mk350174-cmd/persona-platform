# PersonaNeedle Teachers Guide

Teacher modules generate training labels (CEID / drift / voice samples) for the distillation dataset. The pipeline automatically orchestrates available teachers and falls back gracefully to the offline `PersonaMathTeacher` if no API is reachable.

## Overview

### Available Teachers

| Class | Name | Weight | Cost | Requires |
|---|---|---|---|---|
| **AIMLTeacher** | `aiml` | 0.5 | $0 | `AIMLAPI_KEY` |
| **GroqTeacher** | `groq` | 0.3 | $0 | `GROQ_API_KEY` |
| **OpenRouterTeacher** | `openrouter` | 0.2 | $0 | `OPENROUTER_KEY` |
| **ClaudeTeacher** | `claude` | 0.5 | ~$40–70/run | `ANTHROPIC_API_KEY` |
| **GeminiTeacher** | `gemini` | 0.3 | $0 (free tier) | `GEMINI_API_KEY` |
| **LlamaTeacher** | `llama` | 0.2 | $0 (local) | Ollama on `localhost:11434` |
| **PersonaMathTeacher** | `persona_math` | 1.0 | $0 | (fallback, always available) |

### Teacher Interface

All teachers inherit from `BaseTeacher` and implement:

```python
class BaseTeacher(ABC):
    name: str              # unique identifier (e.g., "aiml")
    weight: float          # relative weight in ensemble (0..1, normalized)
    
    @abstractmethod
    def available() -> bool:
        """True if the teacher can serve requests (keys present, APIs reachable)."""
        ...
    
    @abstractmethod
    def generate_ceid_labels(persona_id: str, persona_vector: dict,
                           conversation: str | dict) -> dict:
        """→ {"C": 0..1, "E": 0..1, "I": 0..1, "D": 0..1}"""
        ...
    
    @abstractmethod
    def generate_drift_label(persona_id: str, 
                           conversation_before: str | dict,
                           conversation_after: str | dict) -> dict:
        """→ {"drift": bool, "score": 0..1}"""
        ...
    
    @abstractmethod
    def generate_voice_sample(persona_id: str, persona_vector: dict,
                            prompt: str) -> str:
        """→ a persona-voice reply (text)"""
        ...
```

## Setup Instructions

### 1. Free-Tier Hybrid (Recommended)

Get three free API keys for 100% free training dataset generation.

#### AIML (Claude via OpenAI-compatible API)

1. Go to https://aimlapi.com
2. Sign up (create free account)
3. Navigate to **API Keys** in dashboard
4. Copy your key
5. Add to `.env`:
   ```bash
   AIMLAPI_KEY=your-key-here
   ```

**Details:**
- Model: Claude 3.5 Sonnet
- RPM limit: 60 requests/min
- Cost: Free (up to certain quota)

#### Groq (Fast Llama-70B)

1. Go to https://console.groq.com
2. Sign up (create free account)
3. Navigate to **API Keys**
4. Copy your key
5. Add to `.env`:
   ```bash
   GROQ_API_KEY=your-key-here
   ```

**Details:**
- Model: Llama 3.1 70B Versatile
- RPM limit: 30 requests/min (optimized for 2s/req)
- Quota: 14,400 requests/day free
- Cost: Free tier ✓

#### OpenRouter (Free LLM Fallback)

1. Go to https://openrouter.ai
2. Sign up (create free account)
3. Navigate to **API Keys** / **Settings**
4. Copy your key
5. Add to `.env`:
   ```bash
   OPENROUTER_KEY=your-key-here
   ```

**Details:**
- Model: Llama 3.1 70B Instruct (free)
- RPM limit: 5 requests/min (conservative due to free tier limits)
- Cost: Free tier ✓

### 2. Optional: Premium Teachers

#### Claude (Best CEID Accuracy)

Improves label quality at cost (~$40–70 per full 495-persona run).

1. Go to https://console.anthropic.com/account/keys
2. Create/view your API key
3. Add to `.env`:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-...
   ```

**Cost estimate:**
- Full run (495 personas × 20 conversations × 3 labels): ~$45–65
- Can be mixed with free teachers (weight auto-scales)

#### Gemini (Free Tier, Structured)

Google's generative AI with free quota.

1. Go to https://aistudio.google.com/app/apikey
2. Create/enable Gemini API in your Google Cloud project
3. Copy the API key
4. Add to `.env`:
   ```bash
   GEMINI_API_KEY=your-key-here
   ```

**Details:**
- Model: Gemini 2.0 Flash
- Free quota: Varies by region
- RPM limit: 15 requests/min
- Cost: Free tier ✓

#### Ollama (Local Llama)

Run a local LLM on your machine—no API calls, no cost.

1. Install Ollama: https://ollama.ai (Mac, Windows, Linux)
2. Pull a model:
   ```bash
   ollama pull llama3.2:3b
   # or for better quality (more VRAM required):
   ollama pull llama3.1:70b
   ```
3. Start the server:
   ```bash
   ollama serve
   ```
   This listens on `http://localhost:11434`
4. Run the pipeline:
   ```bash
   python -m needle.training.pipeline \
     --aiml-key $AIMLAPI_KEY \
     --groq-key $GROQ_API_KEY \
     --llama-endpoint http://localhost:11434 \
     --n-conversations 20
   ```

**Details:**
- No API key required
- Model runs locally on your GPU/CPU
- Cost: Free (but requires local hardware)
- Available only if Ollama is running

## Usage Examples

### Example 1: Free-tier hybrid (cost $0)

```bash
export AIMLAPI_KEY="your-aiml-key"
export GROQ_API_KEY="your-groq-key"
export OPENROUTER_KEY="your-openrouter-key"

python -m needle.training.pipeline \
  --aiml-key $AIMLAPI_KEY \
  --groq-key $GROQ_API_KEY \
  --openrouter-key $OPENROUTER_KEY \
  --n-conversations 20
```

**Expected output:**
- Teachers: `['aiml', 'groq', 'openrouter', 'persona_math']` (persona_math is always included as fallback)
- Weights: normalized to sum to 1.0
- Cost: $0

### Example 2: Free-tier + Claude (cost ~$45–65)

```bash
python -m needle.training.pipeline \
  --aiml-key $AIMLAPI_KEY \
  --groq-key $GROQ_API_KEY \
  --openrouter-key $OPENROUTER_KEY \
  --claude-key $ANTHROPIC_API_KEY \
  --n-conversations 20
```

**Expected:**
- Teachers: `['aiml', 'groq', 'openrouter', 'claude', 'persona_math']`
- Weights: Claude (0.5) normalized among all active teachers
- Cost: ~$45–65

### Example 3: With local Ollama

```bash
# In one terminal, start Ollama:
ollama serve

# In another terminal:
python -m needle.training.pipeline \
  --aiml-key $AIMLAPI_KEY \
  --groq-key $GROQ_API_KEY \
  --llama-endpoint http://localhost:11434 \
  --n-conversations 20
```

**Expected:**
- Teachers: `['aiml', 'groq', 'llama', 'persona_math']`
- Llama runs locally, no API calls for that teacher
- Cost: $0

### Example 4: Claude only (simplest, premium)

```bash
python -m needle.training.pipeline \
  --claude-key $ANTHROPIC_API_KEY \
  --n-conversations 20
```

**Expected:**
- Teachers: `['claude', 'persona_math']`
- Cost: ~$45–65
- Good for high-quality labels

### Example 5: Offline demo (no keys, free)

```bash
python -m needle.training.pipeline \
  --limit 3 \
  --n-conversations 4
```

**Expected:**
- Teachers: `['persona_math']` (fallback only)
- No API calls
- Cost: $0
- Fast (offline labels from K-layer vectors)

## How Teachers Work

### 1. Label Generation

Each teacher receives:
- `persona_id`: string (e.g., "socrates")
- `persona_vector`: list/dict (K-layer representation, 495 dims)
- `conversation`: string or dict with `{"text": ..., "pressure": 0–3, ...}`

And returns CEID labels (consistency, epistemic, identity, drift-resistance).

### 2. Weight Normalization

If only some teachers are available, their weights auto-scale. For example:
- Request: AIML (0.5) + Groq (0.3) + OpenRouter (0.2) = 1.0 total
- Actual available: Groq (0.3) + PersonaMath (0.1, co-teacher)
- Normalized: Groq (0.75), PersonaMath (0.25)

### 3. Caching

Each teacher caches responses on-disk (`.teacher_cache/<name>/`), so repeated runs are instant.

### 4. Graceful Fallback

If any teacher fails (API down, rate-limited, bad response), the request automatically retries to `PersonaMathTeacher` (offline) without stopping the pipeline.

## Architecture

### Class Hierarchy

```
BaseTeacher (abstract)
├── ChatCompletionsTeacher (OpenAI-compatible API base)
│   ├── AIMLTeacher
│   ├── GroqTeacher
│   └── OpenRouterTeacher
├── ClaudeTeacher (Anthropic SDK)
├── GeminiTeacher (Google GenAI SDK)
├── LlamaTeacher (HTTP to Ollama)
└── PersonaMathTeacher (offline, persona_math.ceid)
```

### Key Files

- **`base.py`**: `BaseTeacher` abstract interface
- **`_openai_chat.py`**: `ChatCompletionsTeacher` (shared for AIML/Groq/OpenRouter)
- **`_remote.py`**: rate limiting, caching, JSON extraction, retry logic
- **`aiml_teacher.py`**, **`groq_teacher.py`**, **`openrouter_teacher.py`**: free-tier implementations
- **`claude_teacher.py`**, **`gemini_teacher.py`**, **`llama_teacher.py`**: optional premium/local
- **`persona_math_teacher.py`**: offline fallback

### Rate Limiting & Caching

Each teacher respects its RPM limit and caches responses:

| Teacher | RPM | Interval | Cache |
|---|---|---|---|
| AIML | 60 | 1 sec | ✓ |
| Groq | 30 | 2 sec | ✓ |
| OpenRouter | 5 | 12 sec | ✓ |
| Claude | 60 | 1 sec | ✓ |
| Gemini | 15 | 4 sec | ✓ |
| Llama | ∞ | local | ✓ |
| PersonaMath | ∞ | instant | ✓ |

## Testing

Run the teacher tests:

```bash
pytest needle/training/tests/test_teachers.py -v
```

Tests cover:
- ✓ API availability checks (key present / absent)
- ✓ Weight specifications
- ✓ CEID/drift/voice label generation
- ✓ Fallback to PersonaMathTeacher on error
- ✓ Weight normalization
- ✓ Rate limiting
- ✓ Caching

## Troubleshooting

### Issue: "Teacher unavailable: ..."

**Cause:** SDK not installed or API key missing.

**Fix:**
```bash
# Install optional SDKs:
pip install -r needle/training/requirements.txt

# Verify .env:
grep AIML_API_KEY .env
```

### Issue: API rate-limited

**Cause:** Exceeding RPM limit.

**Solution:**
- Use a lower `--n-conversations` (e.g., 5 instead of 20)
- Add `--resume` to checkpoint and resume later
- Use a slower teacher (OpenRouter: 5 rpm) or local Llama

### Issue: All teachers failing

**Expected behavior:** Pipeline falls back to `PersonaMathTeacher` (offline).

**Verify:**
```bash
python -m needle.training.pipeline --limit 1 --n-conversations 2
# Should see: "[pipeline] no API teachers — using offline PersonaMathTeacher fallback"
```

### Issue: Ollama not detected

**Cause:** Ollama not running on `localhost:11434`.

**Fix:**
```bash
# Start Ollama in another terminal:
ollama serve

# Or specify custom endpoint:
python -m needle.training.pipeline \
  --llama-endpoint http://192.168.1.100:11434 \
  --n-conversations 20
```

## Performance & Cost Reference

### Full Run (495 personas, 20 conversations, 3 labels)

**Free-tier hybrid (AIML + Groq + OpenRouter):**
- API calls: ~29,700 weighted
- Cost: $0
- Time: ~8–12 hours (2s/req average, with rate limiting + caching)
- Typical output: 29,700 CEID + 9,900 drift + 9,900 voice labels

**With Claude (adds 0.5 weight):**
- API calls: ~44,550 (increased due to Claude's weight)
- Cost: ~$45–65
- Time: ~12–16 hours
- Better label quality due to Claude's strong persona reasoning

**Claude only:**
- API calls: ~29,700
- Cost: ~$45–65
- Time: ~8–12 hours
- Simplest setup

**Offline (PersonaMathTeacher):**
- API calls: 0
- Cost: $0
- Time: <1 hour (instant K-layer lookups)
- Deterministic labels based on persona vector math

## Next Steps

1. **Choose your setup:** Free-tier hybrid (recommended), Claude, or offline
2. **Get API keys:** Follow the setup instructions above
3. **Update `.env`:** Add your keys
4. **Run the pipeline:**
   ```bash
   python -m needle.training.pipeline \
     --aiml-key $AIMLAPI_KEY \
     --groq-key $GROQ_API_KEY \
     --openrouter-key $OPENROUTER_KEY \
     --n-conversations 20
   ```
5. **Check outputs:** `needle/training/data/ceid_dataset.jsonl` (+ drift, voice, splits)

The dataset feeds into `needle/architecture/distillation.py` for KL distillation into PersonaNeedle.
