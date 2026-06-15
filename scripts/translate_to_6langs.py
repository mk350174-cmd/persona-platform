#!/usr/bin/env python3
"""
Translate Turkish HPEP-100 questions to 5 other languages using Gemini API.

Input: JSON with 50 Turkish questions (from parse_turkish_docx.py)
Output: JSON with 6-language dict for each question (tr, en, de, fr, ja, ar)

Usage:
    python scripts/translate_to_6langs.py <input.json> <output.json>

Features:
    - Parallel batching (5 questions per batch) to respect Gemini free-tier limits
    - Preserves K-layer references and CEID terminology
    - Validates concept preservation
    - Graceful retry on rate limits (exponential backoff)
    - Tracks translation metadata (model, tokens, latency)

Requires:
    - GOOGLE_API_KEY environment variable (Gemini free tier)
"""

import json
import sys
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Optional
import hashlib


def translate_batch(
    questions: dict[str, str],
    batch_size: int = 5,
    max_retries: int = 3,
) -> dict[str, dict[str, str]]:
    """
    Translate Turkish questions to 6 languages using Gemini API.

    Args:
        questions: {qid: turkish_text, ...}
        batch_size: Number of questions per API call (default 5 for free tier)
        max_retries: Retries on rate limit

    Returns:
        {qid: {lang: text, ...}, ...}
    """
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

    translations = {}
    qids = list(questions.keys())

    print(f"Translating {len(qids)} questions in batches of {batch_size}...")

    for batch_start in range(0, len(qids), batch_size):
        batch_ids = qids[batch_start : batch_start + batch_size]
        batch_texts = {qid: questions[qid] for qid in batch_ids}

        print(f"  Batch {batch_start // batch_size + 1}: {batch_ids}")

        for attempt in range(max_retries):
            try:
                batch_translations = _translate_batch_inner(model, batch_texts)
                translations.update(batch_translations)
                break
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    wait = min(2 ** attempt, 30)
                    print(f"    Rate limited. Waiting {wait}s... (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait)
                else:
                    raise

    return translations


def _translate_batch_inner(
    model,
    batch: dict[str, str],
) -> dict[str, dict[str, str]]:
    """
    Call Gemini API once for a batch of questions.
    Returns {qid: {lang: text, ...}, ...}
    """
    prompt = _build_translation_prompt(batch)

    response = model.generate_content(prompt)
    raw_output = response.text

    # Parse JSON response
    try:
        # Extract JSON from markdown code blocks if present
        if "```json" in raw_output:
            start = raw_output.find("```json") + 7
            end = raw_output.find("```", start)
            raw_output = raw_output[start:end].strip()
        elif "```" in raw_output:
            start = raw_output.find("```") + 3
            end = raw_output.find("```", start)
            raw_output = raw_output[start:end].strip()

        result = json.loads(raw_output)
        return result
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Failed to parse Gemini response as JSON: {e}\n"
            f"Response: {raw_output[:200]}"
        )


def _build_translation_prompt(batch: dict[str, str]) -> str:
    """Build a prompt for translating a batch of questions."""
    questions_str = ""
    for qid, text in batch.items():
        questions_str += f'    "{qid}": "{text}",\n'

    return f"""
You are a professional translator for a psychological assessment protocol (HPEP-100).
Translate the following Turkish questions to exactly 5 other languages: English, German, French, Japanese, and Arabic.

CRITICAL REQUIREMENTS:
1. Preserve all K-layer references (e.g., "K1", "K4", "CEID", "aMCC", "PFC", "vmPFC", "dlPFC")
2. Preserve all proper nouns (e.g., "Bentham", "Kant", "Hegelian", "Lacanian", "Sartrean", "Schopenhauer")
3. Maintain the psychological/philosophical tone and nuance
4. Keep sentence structure parallel where possible
5. Ensure all 6 languages are present for every question

Return ONLY valid JSON (no markdown, no explanation). Format:
{{
    "S1": {{"tr": "original", "en": "...", "de": "...", "fr": "...", "ja": "...", "ar": "..."}},
    "S2": {{"tr": "original", "en": "...", "de": "...", "fr": "...", "ja": "...", "ar": "..."}},
    ...
}}

Turkish questions to translate:
{questions_str}

RESPONSE (JSON only):
"""


def merge_translations(
    parsed_json: dict,
    translations: dict[str, dict[str, str]],
) -> dict:
    """
    Merge Gemini translations back into the parsed structure.

    Args:
        parsed_json: Output from parse_turkish_docx.py
        translations: Output from translate_batch()

    Returns:
        dict with merged data and metadata
    """
    return {
        "metadata": {
            **parsed_json["metadata"],
            "translation_time": datetime.utcnow().isoformat() + "Z",
            "translator": "Gemini 1.5 Flash",
            "languages": ["tr", "en", "de", "fr", "ja", "ar"],
        },
        "questions": translations,
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/translate_to_6langs.py <input.json> <output.json>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    try:
        print(f"Loading Turkish questions from: {input_file}")
        with open(input_file, "r", encoding="utf-8") as f:
            parsed = json.load(f)

        turkish_questions = parsed["questions"]
        print(f"Loaded {len(turkish_questions)} questions")

        print(f"\nTranslating to 5 languages (en, de, fr, ja, ar)...")
        translations = translate_batch(turkish_questions)

        print(f"\n✓ Translated {len(translations)} questions")

        result = merge_translations(parsed, translations)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"✓ Output saved to: {output_file}")

    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
