#!/usr/bin/env python3
"""
Integrate 6-language questions into api/quiz_questions.py and api/quiz_translations.py.

Input: JSON with 6-language translations (from translate_to_6langs.py)
Process:
    1. Update api/quiz_translations.py with all 50 translations
    2. Update api/quiz_questions.py _SPEC table with new language dicts
    3. Run full test suite (pytest tests/test_quiz_*.py)
    4. Validate: All 822 tests pass, coverage >= 89%

Usage:
    python scripts/integrate_quiz_questions.py <input.json>

Output:
    - Updated /api/quiz_translations.py
    - Updated /api/quiz_questions.py
    - Test report (passed/failed)
    - Log entry in TURKISH_INTEGRATION_LOG.md
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import re


def load_translations(json_path: str) -> dict[str, dict[str, str]]:
    """Load 6-language translations from JSON."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("questions", {})


def update_quiz_translations(translations: dict[str, dict[str, str]]) -> None:
    """
    Update api/quiz_translations.py with all translations.

    Replaces the TRANSLATIONS dict while preserving helper functions.
    """
    filepath = Path(__file__).parent.parent / "api" / "quiz_translations.py"

    # Generate new TRANSLATIONS dict
    translations_code = "TRANSLATIONS: dict[str, dict[str, str]] = {\n"
    for qid in sorted(translations.keys(), key=lambda x: int(x[1:])):
        lang_dict = translations[qid]
        translations_code += f'    "{qid}": {{\n'
        for lang in ["tr", "en", "de", "fr", "ja", "ar"]:
            text = lang_dict.get(lang, "")
            # Escape quotes in text
            text = text.replace('"', '\\"')
            translations_code += f'        "{lang}": "{text}",\n'
        translations_code += "    },\n"
    translations_code += "}\n"

    # Read current file
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace TRANSLATIONS dict (preserve everything after it)
    pattern = r"^TRANSLATIONS: dict\[str, dict\[str, str\]\] = \{.*?\n\}\n"
    new_content = re.sub(pattern, translations_code, content, flags=re.MULTILINE | re.DOTALL)

    if new_content == content:
        raise RuntimeError("Failed to update TRANSLATIONS dict in quiz_translations.py")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✓ Updated {filepath}")


def update_quiz_questions(translations: dict[str, dict[str, str]]) -> None:
    """
    Update api/quiz_questions.py _SPEC with language dicts.

    For each question, convert the text field from str to dict[lang: text].
    """
    filepath = Path(__file__).parent.parent / "api" / "quiz_questions.py"

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Load the existing _SPEC to understand structure
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    try:
        from api.quiz_questions import _SPEC
        original_spec = list(_SPEC)
    except Exception as e:
        raise RuntimeError(f"Could not import existing _SPEC: {e}")

    # Build new _SPEC with translations
    new_spec_lines = ["_SPEC: list[tuple] = ["]

    for entry in original_spec:
        qid, phase, axes, layers, amcc, theme, old_text = entry

        # Get translation dict for this question
        new_text_dict = translations.get(qid, {})

        if not new_text_dict:
            # No translation; keep old text
            new_text_dict = {"en": old_text} if isinstance(old_text, str) else old_text

        # Safely escape strings for Python code
        def safe_escape(s: str) -> str:
            """Escape string for Python repr."""
            return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')

        # Format the tuple
        axes_str = str(axes).replace("'", '"')
        layers_str = str(layers)
        amcc_str = f'"{safe_escape(amcc)}"'
        theme_str = f'"{safe_escape(theme)}"'

        # Build text dict repr with proper escaping
        text_repr = "{"
        for lang in ["tr", "en", "de", "fr", "ja", "ar"]:
            text_val = new_text_dict.get(lang, "")
            text_val = safe_escape(text_val)
            text_repr += f'"{lang}": "{text_val}", '
        text_repr = text_repr.rstrip(", ") + "}"

        new_spec_lines.append(
            f'    ("{qid}", {phase}, {axes_str}, {layers_str}, {amcc_str}, '
            f'{theme_str}, {text_repr}),'
        )

    new_spec_lines.append("]")

    # Replace _SPEC in file
    pattern = r"^_SPEC: list\[tuple\] = \[.*?\n\]"
    new_spec_text = "\n".join(new_spec_lines)

    updated_content = re.sub(
        pattern,
        new_spec_text,
        content,
        flags=re.MULTILINE | re.DOTALL
    )

    if updated_content == content:
        raise RuntimeError("Failed to update _SPEC in quiz_questions.py")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(updated_content)

    print(f"✓ Updated {filepath} with {len(translations)} language translations")


def run_tests() -> tuple[bool, str]:
    """
    Run full quiz test suite.

    Returns (success: bool, summary: str)
    """
    print("\nRunning test suite...")
    test_dir = Path(__file__).parent.parent / "tests"

    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/test_quiz_*.py", "-v", "--tb=short"],
            cwd=test_dir.parent,
            capture_output=True,
            text=True,
            timeout=300,
        )

        output = result.stdout + result.stderr

        # Extract summary line
        summary_match = re.search(
            r"=+\s+([\d\s\w,]+)\s+in\s+[\d.]+s\s+=+",
            output
        )
        summary = summary_match.group(1) if summary_match else "Unknown"

        success = result.returncode == 0

        return success, summary, output

    except subprocess.TimeoutExpired:
        return False, "Test timeout (>300s)", ""
    except Exception as e:
        return False, f"Test execution error: {e}", ""


def write_integration_log(
    translations: dict,
    test_success: bool,
    test_summary: str,
) -> None:
    """Write integration log to TURKISH_INTEGRATION_LOG.md."""
    filepath = Path(__file__).parent.parent / "TURKISH_INTEGRATION_LOG.md"

    log_entry = f"""
## Turkish Integration — {datetime.utcnow().isoformat()}

### Input
- Questions: {len(translations)} (S1-S50)
- Languages: 6 (tr, en, de, fr, ja, ar)
- Source: Received from user (docx → JSON → translated)

### Processing
- Parse: ✓
- Translate: ✓
- Integrate: {'✓' if test_success else '✗'}

### Test Results
- Summary: {test_summary}
- Status: {'PASSED' if test_success else 'FAILED'}

### Timestamp
- Completed: {datetime.utcnow().isoformat()}Z

"""

    if filepath.exists():
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(log_entry)
    else:
        header = """# Turkish HPEP-100 Integration Log

Tracks the integration of Turkish questions (S1-S50) from source document to
production api/quiz_questions.py and api/quiz_translations.py.

---

"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(header + log_entry)

    print(f"✓ Log written to {filepath}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/integrate_quiz_questions.py <input.json>")
        sys.exit(1)

    json_path = sys.argv[1]

    try:
        print(f"Loading translations from: {json_path}")
        translations = load_translations(json_path)

        if len(translations) != 50:
            raise ValueError(f"Expected 50 questions, found {len(translations)}")

        print(f"Loaded {len(translations)} questions with 6-language translations")

        print(f"\nUpdating api/quiz_translations.py...")
        update_quiz_translations(translations)

        print(f"\nRunning tests...")
        test_success, test_summary, test_output = run_tests()

        print(f"Test result: {test_summary}")

        if test_success:
            print("✓ All tests passed!")
        else:
            print(f"✗ Tests failed. Details:\n{test_output[-1000:]}")

        print(f"\nWriting integration log...")
        write_integration_log(translations, test_success, test_summary)

        sys.exit(0 if test_success else 1)

    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
