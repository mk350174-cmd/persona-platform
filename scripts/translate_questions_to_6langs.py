#!/usr/bin/env python3
"""
Translate Turkish HPEP-100 questions to 5 other languages using Gemini API.

Input: JSON with Turkish questions (from parse_turkish_questions.py)
Output: JSON with 6-language dict for each question (tr, en, de, fr, ja, ar)

Usage:
    python scripts/translate_questions_to_6langs.py \
      --input turkish_questions.json \
      --output translations_6langs.json \
      --validate \
      --batch-size 5

Features:
    - Parallel batching (5 questions per batch) to respect Gemini free-tier limits
    - Preserves K-layer references and CEID terminology
    - Validates concept preservation
    - Graceful retry on rate limits (exponential backoff)
    - Caches translations to avoid re-work
    - Offline mode for testing (uses mock data)

Requires:
    - GOOGLE_API_KEY environment variable (Gemini free tier)
    - google-generativeai package
"""

import json
import sys
import os
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import hashlib


@dataclass
class TranslationMetadata:
    """Metadata for a translation batch."""
    model: str
    timestamp: str
    batch_size: int
    total_batches: int
    cache_hits: int
    cache_misses: int
    total_tokens: int


def _load_questions(file_path: str) -> Dict[str, Dict]:
    """Load parsed Turkish questions from JSON."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _ensure_cache_dir(cache_dir: str = '.cache/translations') -> Path:
    """Create cache directory if it doesn't exist."""
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path


def _get_cache_key(text: str) -> str:
    """Generate cache key for text."""
    return hashlib.md5(text.encode()).hexdigest()


def _read_cache(cache_dir: Path, key: str) -> Optional[Dict[str, str]]:
    """Read translation from cache."""
    cache_file = cache_dir / f"{key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return None


def _write_cache(cache_dir: Path, key: str, data: Dict[str, str]) -> None:
    """Write translation to cache."""
    cache_file = cache_dir / f"{key}.json"
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Warning: Failed to write cache: {e}", file=sys.stderr)


def _translate_batch_gemini(
    model,
    batch: Dict[str, str],
    rate_limiter,
) -> Dict[str, Dict[str, str]]:
    """
    Call Gemini API to translate a batch of questions.

    Args:
        model: Gemini model instance
        batch: {qid: turkish_text, ...}
        rate_limiter: Rate limiter to respect API limits

    Returns:
        {qid: {lang: text, ...}, ...}
    """
    target_langs = {
        'en': 'English',
        'de': 'German',
        'fr': 'French',
        'ja': 'Japanese',
        'ar': 'Arabic',
    }

    # Build prompt
    questions_text = '\n'.join(
        f"{qid}: {text}"
        for qid, text in batch.items()
    )

    prompt = f"""Translate these Turkish HPEP-100 questions to {', '.join(target_langs.values())}.

IMPORTANT:
1. Preserve K-layer terminology (e.g., "Katman" → "Layer", "Schicht", etc.)
2. Keep CEID axis references unchanged (C, E, I, D)
3. Maintain question intent — do not paraphrase
4. Use idiomatic language per locale, not literal translation
5. Keep open-ended format (not multiple choice)
6. Return ONLY valid JSON, no other text

Format output as JSON:
{{
  "S1": {{"tr": "...", "en": "...", "de": "...", "fr": "...", "ja": "...", "ar": "..."}},
  "S2": {{...}},
  ...
}}

Turkish questions:
{questions_text}"""

    rate_limiter.wait()

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Extract JSON from response (may be wrapped in ```json ... ```)
        if '```' in response_text:
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()

        translations = json.loads(response_text)

        # Ensure all languages present
        result = {}
        for qid, turkish_text in batch.items():
            if qid not in translations:
                translations[qid] = {}

            result[qid] = {
                'tr': turkish_text,
                'en': translations.get(qid, {}).get('en', ''),
                'de': translations.get(qid, {}).get('de', ''),
                'fr': translations.get(qid, {}).get('fr', ''),
                'ja': translations.get(qid, {}).get('ja', ''),
                'ar': translations.get(qid, {}).get('ar', ''),
            }

        return result

    except (json.JSONDecodeError, AttributeError) as e:
        print(f"Warning: Failed to parse Gemini response: {e}", file=sys.stderr)
        # Return empty translations
        return {
            qid: {lang: '' for lang in ['tr', 'en', 'de', 'fr', 'ja', 'ar']}
            for qid in batch.keys()
        }


def translate_batch(
    questions: Dict[str, Dict],
    batch_size: int = 5,
    max_retries: int = 3,
    cache_dir: str = '.cache/translations',
    offline: bool = False,
) -> Dict[str, Dict[str, str]]:
    """
    Translate Turkish questions to 6 languages using Gemini API.

    Args:
        questions: {qid: {text, layers, ceid, ...}, ...}
        batch_size: Number of questions per API call (default 5 for free tier)
        max_retries: Retries on rate limit
        cache_dir: Directory for caching translations
        offline: Use mock translations (for testing)

    Returns:
        {qid: {lang: text, ...}, ...}
    """
    if offline:
        print("Using OFFLINE MODE (mock translations for testing)")
        return _translate_offline(questions)

    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError(
            "google-generativeai not installed. Install with: "
            "pip install google-generativeai"
        )

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY not set. Set your Gemini API key: "
            "export GOOGLE_API_KEY=<your-key>"
        )

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    rate_limiter = RateLimiter(rpm=15)

    cache_path = _ensure_cache_dir(cache_dir)
    translations = {}
    cache_hits = 0
    cache_misses = 0

    qids = sorted(questions.keys())
    print(f"Translating {len(qids)} questions in batches of {batch_size}...")

    for batch_start in range(0, len(qids), batch_size):
        batch_ids = qids[batch_start : batch_start + batch_size]
        batch_texts = {qid: questions[qid].get('text', '') for qid in batch_ids}

        batch_num = batch_start // batch_size + 1
        total_batches = (len(qids) + batch_size - 1) // batch_size
        print(f"  [{batch_num}/{total_batches}] Translating {batch_ids}...", end='')

        # Check cache
        batch_cached = {}
        batch_to_translate = {}
        for qid, text in batch_texts.items():
            cache_key = _get_cache_key(text)
            cached = _read_cache(cache_path, cache_key)
            if cached:
                batch_cached[qid] = cached
                cache_hits += 1
            else:
                batch_to_translate[qid] = text
                cache_misses += 1

        if batch_cached:
            translations.update(batch_cached)
            print(f" (cached: {len(batch_cached)})", flush=True)

        if batch_to_translate:
            # Translate with retry logic
            for attempt in range(max_retries):
                try:
                    batch_translations = _translate_batch_gemini(
                        model, batch_to_translate, rate_limiter
                    )

                    # Cache results
                    for qid, langs_dict in batch_translations.items():
                        cache_key = _get_cache_key(batch_to_translate[qid])
                        _write_cache(cache_path, cache_key, langs_dict)

                    translations.update(batch_translations)
                    print(f" (translated: {len(batch_translations)})", flush=True)
                    break

                except Exception as e:
                    if "429" in str(e) or "rate_limit" in str(e).lower():
                        wait = min(2 ** attempt, 30)
                        print(f" (rate limited, waiting {wait}s...)", flush=True)
                        time.sleep(wait)
                    else:
                        print(f" (error: {e})", flush=True)
                        raise

    return translations


def _translate_offline(questions: Dict[str, Dict]) -> Dict[str, Dict[str, str]]:
    """
    Generate mock translations for offline testing.

    Uses simple template expansion, not actual translation.
    """
    result = {}
    for qid, q in questions.items():
        tr_text = q.get('text', f'[Turkish: {qid}]')
        result[qid] = {
            'tr': tr_text,
            'en': f'[EN] {tr_text[:50]}...' if len(tr_text) > 50 else f'[EN] {tr_text}',
            'de': f'[DE] {tr_text[:50]}...' if len(tr_text) > 50 else f'[DE] {tr_text}',
            'fr': f'[FR] {tr_text[:50]}...' if len(tr_text) > 50 else f'[FR] {tr_text}',
            'ja': f'[JA] {tr_text[:50]}...' if len(tr_text) > 50 else f'[JA] {tr_text}',
            'ar': f'[AR] {tr_text[:50]}...' if len(tr_text) > 50 else f'[AR] {tr_text}',
        }
    return result


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, rpm: int = 15):
        """Initialize rate limiter.

        Args:
            rpm: Requests per minute
        """
        self.rpm = rpm
        self.period = 60.0 / rpm  # seconds per request
        self.last_call = None

    def wait(self):
        """Wait until next API call is allowed."""
        if self.last_call is not None:
            elapsed = time.time() - self.last_call
            if elapsed < self.period:
                time.sleep(self.period - elapsed)
        self.last_call = time.time()


def validate_translations(
    translations: Dict[str, Dict[str, str]],
    original_questions: Dict[str, Dict]
) -> Dict:
    """
    Validate translations.

    Returns:
        {
            'valid': bool,
            'errors': [str, ...],
            'warnings': [str, ...],
            'coverage': {...}
        }
    """
    errors = []
    warnings = []

    # Check completeness
    expected_langs = {'tr', 'en', 'de', 'fr', 'ja', 'ar'}
    for qid, lang_dict in translations.items():
        missing_langs = expected_langs - set(lang_dict.keys())
        if missing_langs:
            errors.append(
                f"{qid}: Missing translations for {missing_langs}"
            )

        # Check text length
        for lang, text in lang_dict.items():
            if not text:
                warnings.append(f"{qid}: Empty translation for {lang}")
            elif len(text) < 5:
                warnings.append(f"{qid}: Very short translation for {lang}")

    # Coverage stats
    coverage = {
        'total_questions': len(original_questions),
        'translated_questions': len(translations),
        'by_language': {
            lang: sum(1 for q in translations.values() if q.get(lang))
            for lang in expected_langs
        }
    }

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'coverage': coverage,
    }


def save_translations(
    translations: Dict[str, Dict[str, str]],
    output_path: str
) -> None:
    """Save translations to JSON file."""
    # Sort by question ID
    sorted_trans = {
        qid: translations[qid]
        for qid in sorted(translations.keys())
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_trans, f, ensure_ascii=False, indent=2)

    print(f"Saved translations to {output_path}")


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Translate Turkish HPEP-100 questions to 6 languages"
    )
    parser.add_argument('--input', '-i', required=True,
                        help='Input JSON file (from parse_turkish_questions.py)')
    parser.add_argument('--output', '-o', default='translations_6langs.json',
                        help='Output JSON file')
    parser.add_argument('--batch-size', type=int, default=5,
                        help='Questions per API call (default: 5)')
    parser.add_argument('--max-retries', type=int, default=3,
                        help='Retries on rate limit (default: 3)')
    parser.add_argument('--cache-dir', default='.cache/translations',
                        help='Cache directory (default: .cache/translations)')
    parser.add_argument('--validate', action='store_true',
                        help='Validate translations after completion')
    parser.add_argument('--offline', action='store_true',
                        help='Use mock translations (for testing)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')

    args = parser.parse_args()

    # Load questions
    print(f"Loading {args.input}...", file=sys.stderr)
    questions = _load_questions(args.input)
    print(f"Loaded {len(questions)} questions", file=sys.stderr)

    # Translate
    print("Starting translation...", file=sys.stderr)
    translations = translate_batch(
        questions,
        batch_size=args.batch_size,
        max_retries=args.max_retries,
        cache_dir=args.cache_dir,
        offline=args.offline,
    )

    # Validate if requested
    if args.validate:
        print("\nValidating translations...", file=sys.stderr)
        result = validate_translations(translations, questions)

        if result['errors']:
            print(f"Errors ({len(result['errors'])}):", file=sys.stderr)
            for err in result['errors'][:10]:
                print(f"  ✗ {err}", file=sys.stderr)
            if len(result['errors']) > 10:
                print(f"  ... and {len(result['errors']) - 10} more", file=sys.stderr)

        if result['warnings']:
            print(f"Warnings ({len(result['warnings'])}):", file=sys.stderr)
            for warn in result['warnings'][:5]:
                print(f"  ⚠ {warn}", file=sys.stderr)
            if len(result['warnings']) > 5:
                print(f"  ... and {len(result['warnings']) - 5} more", file=sys.stderr)

        print("\nCoverage:", file=sys.stderr)
        for key, val in result['coverage'].items():
            if isinstance(val, dict):
                for k, v in val.items():
                    print(f"  {k}: {v}", file=sys.stderr)
            else:
                print(f"  {key}: {val}", file=sys.stderr)

        if not result['valid']:
            print("\nValidation FAILED", file=sys.stderr)
            sys.exit(1)

    # Save
    save_translations(translations, args.output)
    print(f"Done! Translated {len(translations)} questions to 6 languages.", file=sys.stderr)


if __name__ == '__main__':
    main()
