#!/usr/bin/env python3
"""
Parse Turkish HPEP-100 questions from Word document (.docx).

Extracts question text, K-layer references, CEID axes, and metadata.
Validates against HPEP-100 schema.

Usage:
    python scripts/parse_turkish_questions.py \
      --input questions.docx \
      --output turkish_questions.json \
      --validate
"""

import json
import sys
import re
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict


@dataclass
class ParsedQuestion:
    """Represents a parsed HPEP-100 question."""
    id: str
    text: str
    layers: List[int]
    ceid: List[str]
    phase: int
    theme: str
    amcc: str


# Expected phase assignments (S1-S5 Phase 1, S6-S10 Phase 2, etc.)
PHASE_MAP = {
    (1, 5): 1,      # S1-S5 → Phase 1
    (6, 10): 2,     # S6-S10 → Phase 2
    (11, 15): 3,    # S11-S15 → Phase 3
    (16, 20): 4,    # S16-S20 → Phase 4
    (21, 25): 5,    # S21-S25 → Phase 5
    (26, 30): 6,    # S26-S30 → Phase 6
    (31, 35): 7,    # S31-S35 → Phase 7
    (36, 40): 8,    # S36-S40 → Phase 8
    (41, 45): 9,    # S41-S45 → Phase 9
    (46, 50): 10,   # S46-S50 → Phase 10
}

# Known themes from HPEP-100
KNOWN_THEMES = {
    "S1": "Cosmology: is reality rigid causality, chaos, or hybrid?",
    "S2": "Epistemic threshold: concrete evidence / logic chain / intuition?",
    "S3": "Core motivation / hidden goal (effort-value-reward).",
    "S4": "Moral red line + personal irritant (K4 probe).",
    "S5": "Paradox response: continue / collapse / transform?",
    "S50": "The Architect's Mirror — founding commitment under self-revelation.",
}


def _get_phase_for_question(qid: str) -> int:
    """Determine phase from question ID."""
    try:
        num = int(qid[1:])  # "S1" → 1
        for (low, high), phase in PHASE_MAP.items():
            if low <= num <= high:
                return phase
    except (ValueError, IndexError):
        pass
    return 0


def _parse_k_layers(text: str) -> List[int]:
    """
    Extract K-layer indices from text.

    Recognizes formats:
    - "K0, K7" or "K0,K7"
    - "Katman 0, 7" (Turkish)
    - "[0, 7]" (JSON array)
    - "0, 7" (bare numbers)
    """
    layers = []

    # Try "Katman X, Y" format (Turkish)
    katman_match = re.findall(r'Katman\s+(\d+)', text, re.IGNORECASE)
    if katman_match:
        layers = [int(k) for k in katman_match]
        return sorted(set(layers))

    # Try "KX, KY" format
    k_match = re.findall(r'K(\d+)', text, re.IGNORECASE)
    if k_match:
        layers = [int(k) for k in k_match]
        return sorted(set(layers))

    # Try "[X, Y]" JSON array format
    json_match = re.search(r'\[(\d+(?:\s*,\s*\d+)*)\]', text)
    if json_match:
        layers = [int(n.strip()) for n in json_match.group(1).split(',')]
        return sorted(set(layers))

    # Try bare comma-separated numbers
    bare_match = re.findall(r'\b(\d+)\b', text)
    if bare_match:
        candidates = [int(n) for n in bare_match if 0 <= int(n) <= 99]
        if candidates:
            return sorted(set(candidates))

    return []


def _parse_ceid_axes(text: str) -> List[str]:
    """
    Extract CEID axes from text.

    Recognizes formats:
    - "C" or "[C]"
    - "C, E, I" or "C E I"
    - "CEID" shorthand
    """
    axes = set()

    # Match any of C, E, I, D
    for axis in ['C', 'E', 'I', 'D']:
        if re.search(rf'\b{axis}\b', text):
            axes.add(axis)

    return sorted(list(axes)) if axes else ['E']  # Default to E


def _parse_amcc(text: str) -> str:
    """Extract aMCC engagement level (critical, medium, indirect, low)."""
    for level in ['critical', 'medium', 'indirect', 'low']:
        if level in text.lower():
            return level
    return 'indirect'  # Default


def parse_docx(file_path: str) -> List[ParsedQuestion]:
    """
    Parse Turkish questions from Word document.

    Args:
        file_path: Path to .docx file

    Returns:
        List of ParsedQuestion objects
    """
    try:
        from docx import Document
    except ImportError:
        raise ImportError(
            "python-docx not installed. Install with: pip install python-docx"
        )

    doc = Document(file_path)
    questions = []
    current_qid = None
    current_text_parts = []
    current_metadata = {}

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # Look for question ID (e.g., "S1:", "S1 —", "S1 |")
        qid_match = re.match(r'^(S\d+)\s*[:—|]', text)
        if qid_match:
            # Save previous question
            if current_qid:
                q = _finalize_question(
                    current_qid,
                    ' '.join(current_text_parts),
                    current_metadata
                )
                if q:
                    questions.append(q)

            # Start new question
            current_qid = qid_match.group(1)
            current_text_parts = []
            current_metadata = {
                'line': text,
                'ceid': _parse_ceid_axes(text),
                'layers': _parse_k_layers(text),
                'amcc': _parse_amcc(text),
            }
        elif current_qid:
            current_text_parts.append(text)

    # Save final question
    if current_qid:
        q = _finalize_question(
            current_qid,
            ' '.join(current_text_parts),
            current_metadata
        )
        if q:
            questions.append(q)

    return questions


def _finalize_question(
    qid: str,
    text: str,
    metadata: Dict[str, Any]
) -> Optional[ParsedQuestion]:
    """Finalize a parsed question with validation."""
    text = text.strip()
    if not text or len(text) < 10:
        return None

    phase = _get_phase_for_question(qid)
    layers = metadata.get('layers', [])
    ceid = metadata.get('ceid', ['E'])
    amcc = metadata.get('amcc', 'indirect')
    theme = KNOWN_THEMES.get(qid, '')

    return ParsedQuestion(
        id=qid,
        text=text,
        layers=layers,
        ceid=ceid,
        phase=phase,
        theme=theme,
        amcc=amcc,
    )


def validate_questions(questions: List[ParsedQuestion]) -> Dict[str, Any]:
    """
    Validate parsed questions against HPEP-100 schema.

    Returns:
        {
            'valid': bool,
            'errors': [str, ...],
            'warnings': [str, ...],
            'stats': {...}
        }
    """
    errors = []
    warnings = []

    if len(questions) != 50:
        errors.append(f"Expected 50 questions, got {len(questions)}")

    qid_set = set()
    for q in questions:
        # Check ID format
        if not re.match(r'^S\d+$', q.id):
            errors.append(f"Invalid ID format: {q.id}")
        qid_set.add(q.id)

        # Check required fields
        if not q.text or len(q.text) < 10:
            errors.append(f"{q.id}: Text too short or empty")

        # Check K-layers
        if q.layers:
            for layer in q.layers:
                if not (0 <= layer <= 99):
                    errors.append(f"{q.id}: Invalid K-layer index {layer}")
        else:
            warnings.append(f"{q.id}: No K-layers specified")

        # Check CEID axes
        invalid_axes = set(q.ceid) - {'C', 'E', 'I', 'D'}
        if invalid_axes:
            errors.append(f"{q.id}: Invalid CEID axes: {invalid_axes}")

        # Check phase
        if not (1 <= q.phase <= 10):
            errors.append(f"{q.id}: Invalid phase {q.phase}")

        # Check amcc
        if q.amcc not in {'critical', 'medium', 'indirect', 'low'}:
            errors.append(f"{q.id}: Invalid aMCC level {q.amcc}")

    # Check for missing questions
    for i in range(1, 51):
        qid = f"S{i}"
        if qid not in qid_set:
            warnings.append(f"Missing question {qid}")

    # Stats
    stats = {
        'total': len(questions),
        'with_layers': sum(1 for q in questions if q.layers),
        'with_ceid': sum(1 for q in questions if q.ceid),
        'by_amcc': {
            'critical': sum(1 for q in questions if q.amcc == 'critical'),
            'medium': sum(1 for q in questions if q.amcc == 'medium'),
            'indirect': sum(1 for q in questions if q.amcc == 'indirect'),
            'low': sum(1 for q in questions if q.amcc == 'low'),
        },
    }

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'stats': stats,
    }


def save_json(questions: List[ParsedQuestion], output_path: str) -> None:
    """Save parsed questions to JSON file."""
    data = {
        q.id: asdict(q)
        for q in sorted(questions, key=lambda q: q.id)
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(questions)} questions to {output_path}")


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Parse Turkish HPEP-100 questions from Word document"
    )
    parser.add_argument('--input', '-i', required=True,
                        help='Input .docx file')
    parser.add_argument('--output', '-o', default='turkish_questions.json',
                        help='Output JSON file (default: turkish_questions.json)')
    parser.add_argument('--validate', action='store_true',
                        help='Validate questions after parsing')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')

    args = parser.parse_args()

    # Check input file exists
    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Parse
    print(f"Parsing {args.input}...", file=sys.stderr)
    questions = parse_docx(args.input)

    if args.verbose:
        for q in questions[:3]:  # Show first 3
            print(f"  {q.id}: {q.text[:80]}...", file=sys.stderr)

    # Validate if requested
    if args.validate:
        print("Validating...", file=sys.stderr)
        result = validate_questions(questions)

        if result['errors']:
            print(f"Errors ({len(result['errors'])}):", file=sys.stderr)
            for err in result['errors']:
                print(f"  ✗ {err}", file=sys.stderr)

        if result['warnings']:
            print(f"Warnings ({len(result['warnings'])}):", file=sys.stderr)
            for warn in result['warnings']:
                print(f"  ⚠ {warn}", file=sys.stderr)

        print("\nStats:", file=sys.stderr)
        for key, val in result['stats'].items():
            if isinstance(val, dict):
                print(f"  {key}:", file=sys.stderr)
                for k, v in val.items():
                    print(f"    {k}: {v}", file=sys.stderr)
            else:
                print(f"  {key}: {val}", file=sys.stderr)

        if not result['valid']:
            print("\nValidation FAILED", file=sys.stderr)
            sys.exit(1)
        else:
            print("\nValidation PASSED", file=sys.stderr)

    # Save
    save_json(questions, args.output)
    print(f"Done! Parsed {len(questions)} questions.", file=sys.stderr)


if __name__ == '__main__':
    main()
