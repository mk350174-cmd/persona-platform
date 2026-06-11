#!/usr/bin/env python3
"""Check for placeholder and TODO code in production API."""

import re
import sys


# Placeholders that block commit to api/ (production code)
BLOCKING_PATTERNS = {
    'TODO': r'\bTODO\b',
    'FIXME': r'\bFIXME\b',
    'XXX': r'\bXXX\b',
    'HACK': r'\bHACK\b',
    'PLACEHOLDER': r'\bPLACEHOLDER\b',
    'HARDCODED': r'\bhardcoded\b',  # Case-insensitive
    'TEMPORARY': r'\bTEMPORARY\b',
}

# Exceptions: files/lines allowed to have TODOs
EXCEPTIONS = {
    'api/main.py': [],  # No exceptions for main.py - it's critical
    'api/payments.py': [],
    'api/auth.py': [],
    'api/db.py': [],
}


def check_placeholder_code(filepath):
    """Check for placeholder code in production API files."""
    # Only check api/ files
    if not filepath.startswith('api/'):
        return True

    with open(filepath) as f:
        lines = f.readlines()

    errors = []
    for line_num, line in enumerate(lines, 1):
        # Skip comments that are explicitly marked @production-ready
        if '@production-ready' in line:
            continue

        for pattern_name, pattern in BLOCKING_PATTERNS.items():
            if re.search(pattern, line, re.IGNORECASE):
                # Check if there are exceptions for this file/line
                file_exceptions = EXCEPTIONS.get(filepath, [])
                if line_num in file_exceptions:
                    continue

                errors.append({
                    'line': line_num,
                    'pattern': pattern_name,
                    'text': line.rstrip(),
                })

    if errors:
        print(f"ERROR: {filepath} contains placeholder/TODO code (production code must be complete)")
        for error in errors:
            print(f"  Line {error['line']}: {error['pattern']}")
            print(f"    {error['text']}")
        print()
        print("  → Complete the implementation OR mark as @production-ready")
        print("  → Example: # @production-ready: Intentional placeholder (see issue #X)")
        return False

    return True


def main():
    """Check all provided files."""
    all_ok = True
    for filepath in sys.argv[1:]:
        if filepath.endswith('.py'):
            if not check_placeholder_code(filepath):
                all_ok = False

    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
