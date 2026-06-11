#!/usr/bin/env python3
"""Check that pytest fixtures are only defined in conftest.py."""

import re
import sys


def check_fixtures(filepath):
    """Check if file has @pytest.fixture definitions outside conftest.py."""
    if "conftest.py" in filepath:
        return True

    with open(filepath) as f:
        content = f.read()

    # Find @pytest.fixture definitions (including multi-line decorators)
    fixture_pattern = r'@pytest\.fixture(?:\([^)]*\))?\s*\ndef\s+(\w+)'
    fixtures = re.findall(fixture_pattern, content, re.MULTILINE | re.DOTALL)

    if fixtures:
        print(f"ERROR: {filepath} has pytest fixtures: {fixtures}")
        print("  → Move all pytest fixtures to tests/conftest.py")
        print("  → This ensures fixture reuse and consistent test setup")
        return False

    return True


def main():
    """Check all provided test files."""
    all_ok = True
    for filepath in sys.argv[1:]:
        if filepath.endswith('.py') and ('test_' in filepath or 'conftest' in filepath):
            if not check_fixtures(filepath):
                all_ok = False

    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
