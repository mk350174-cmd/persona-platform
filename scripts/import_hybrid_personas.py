#!/usr/bin/env python3
"""
Phase 6: Bulk import of 48 hybrid personas from hybrid_personas_raw.jsonl

Features:
  - Load each line from data/hybrid_personas_raw.jsonl
  - Validate K-layer indices [1-98]
  - Check unique constraints (persona_id, combination_number)
  - Progress bar with tqdm
  - Error handling and logging
  - Summary report with statistics

Usage:
  python scripts/import_hybrid_personas.py
  python scripts/import_hybrid_personas.py --input data/hybrid_personas_raw.jsonl
  python scripts/import_hybrid_personas.py --input data/hybrid_personas_raw.jsonl --clear  # Truncate first

Requires:
  - Database already initialized (api/db.py)
  - Alembic migration 009 applied
  - Python 3.11+
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import argparse

# Add repo root to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from api.db import SessionLocal, HybridPersona, Base, engine
from sqlalchemy.exc import IntegrityError
import secrets

try:
    from tqdm import tqdm
except ImportError:
    print("ERROR: tqdm not installed. Install with: pip install tqdm")
    sys.exit(1)


class ImportStats:
    """Track import statistics."""
    def __init__(self):
        self.total_lines = 0
        self.imported = 0
        self.skipped = 0
        self.errors = 0
        self.error_details = []
        self.start_time = datetime.now(timezone.utc)

    def add_error(self, row_num: int, persona_id: str, reason: str):
        """Record an error."""
        self.errors += 1
        self.error_details.append({
            'row': row_num,
            'persona_id': persona_id,
            'reason': reason,
        })

    def duration_seconds(self) -> float:
        """Return elapsed time in seconds."""
        elapsed = datetime.now(timezone.utc) - self.start_time
        return elapsed.total_seconds()

    def print_summary(self):
        """Print summary report."""
        print("\n" + "=" * 70)
        print("IMPORT SUMMARY REPORT")
        print("=" * 70)
        print(f"Total lines read:        {self.total_lines}")
        print(f"Successfully imported:   {self.imported}")
        print(f"Skipped:                 {self.skipped}")
        print(f"Errors:                  {self.errors}")
        print(f"Duration:                {self.duration_seconds():.2f}s")
        print("=" * 70)

        if self.error_details:
            print("\nERRORS ENCOUNTERED:")
            for err in self.error_details:
                print(f"  Row {err['row']}: {err['persona_id']} — {err['reason']}")
        else:
            print("\nNO ERRORS ENCOUNTERED ✓")

        print("=" * 70)


def validate_k_layers(layers: list, field_name: str) -> Optional[str]:
    """Validate K-layer indices. Returns error message or None if valid."""
    if not isinstance(layers, list):
        return f"{field_name} must be a list, got {type(layers).__name__}"
    if not layers:
        return f"{field_name} cannot be empty"
    for layer in layers:
        if not isinstance(layer, int):
            return f"{field_name} contains non-integer: {layer}"
        if layer < 1 or layer > 98:
            return f"{field_name} contains out-of-range index: {layer} (must be 1-98)"
    return None


def load_and_import_personas(
    input_file: Path,
    clear_existing: bool = False,
    db_session=None,
) -> ImportStats:
    """
    Load personas from JSONL file and import to database.

    Args:
        input_file: Path to hybrid_personas_raw.jsonl
        clear_existing: If True, truncate hybrid_personas table first
        db_session: SQLAlchemy session (creates new if None)

    Returns:
        ImportStats object with summary
    """
    stats = ImportStats()

    # Use provided session or create new one
    session = db_session or SessionLocal()
    should_close_session = db_session is None

    try:
        # Clear existing if requested
        if clear_existing:
            print("Clearing existing hybrid personas...")
            session.query(HybridPersona).delete()
            session.commit()
            print("  ✓ Cleared")

        # Read file
        if not input_file.exists():
            print(f"ERROR: File not found: {input_file}")
            return stats

        print(f"\nReading {input_file}...")

        # Count lines for progress bar
        with open(input_file) as f:
            total_lines = sum(1 for _ in f)

        stats.total_lines = total_lines

        # Import personas
        with open(input_file) as f:
            seen_persona_ids = set()
            seen_numbers = set()

            for row_num, line in enumerate(tqdm(f, total=total_lines, desc="Importing"), 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)

                    # Extract fields
                    persona_id = data.get('id')
                    number = data.get('number')
                    name_tr = data.get('name_tr')
                    name_en = data.get('name_en')
                    use_case = data.get('use_case')
                    characteristic = data.get('characteristic')
                    active_layers = data.get('active_layers', [])
                    suppressed_layers = data.get('suppressed_layers', [])

                    # Validate required fields
                    if not persona_id:
                        stats.add_error(row_num, str(persona_id), "Missing 'id' field")
                        stats.skipped += 1
                        continue

                    if not number:
                        stats.add_error(row_num, persona_id, "Missing 'number' field")
                        stats.skipped += 1
                        continue

                    if not name_tr or not name_en:
                        stats.add_error(row_num, persona_id, "Missing name_tr or name_en")
                        stats.skipped += 1
                        continue

                    if not use_case or not characteristic:
                        stats.add_error(row_num, persona_id, "Missing use_case or characteristic")
                        stats.skipped += 1
                        continue

                    # Validate K-layers
                    err = validate_k_layers(active_layers, "active_layers")
                    if err:
                        stats.add_error(row_num, persona_id, err)
                        stats.skipped += 1
                        continue

                    err = validate_k_layers(suppressed_layers, "suppressed_layers")
                    if err:
                        stats.add_error(row_num, persona_id, err)
                        stats.skipped += 1
                        continue

                    # Check for duplicates
                    if persona_id in seen_persona_ids:
                        stats.add_error(row_num, persona_id, "Duplicate persona_id")
                        stats.skipped += 1
                        continue

                    if number in seen_numbers:
                        stats.add_error(row_num, persona_id, f"Duplicate combination_number: {number}")
                        stats.skipped += 1
                        continue

                    seen_persona_ids.add(persona_id)
                    seen_numbers.add(number)

                    # Create record
                    persona = HybridPersona(
                        id=secrets.token_hex(16),
                        persona_id=persona_id,
                        combination_number=number,
                        name_tr=name_tr,
                        name_en=name_en,
                        use_case=use_case,
                        characteristic=characteristic,
                        active_k_layers=active_layers,
                        suppressed_k_layers=suppressed_layers,
                        example_outputs=data.get('example_outputs'),
                        price_usd=data.get('price_usd', 1499),  # Default: 14.99 USD
                        is_available=True,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )

                    session.add(persona)
                    stats.imported += 1

                except json.JSONDecodeError as e:
                    stats.add_error(row_num, "?", f"JSON decode error: {e}")
                    stats.skipped += 1
                except Exception as e:
                    stats.add_error(row_num, data.get('id', '?'), f"Exception: {str(e)}")
                    stats.skipped += 1

            # Commit all changes
            try:
                session.commit()
                print(f"\n✓ Committed {stats.imported} personas to database")
            except IntegrityError as e:
                session.rollback()
                print(f"\n✗ Integrity error on commit: {e}")
                stats.errors += (stats.imported - stats.errors)
                stats.imported = 0

    finally:
        if should_close_session:
            session.close()

    # Print summary
    stats.print_summary()

    return stats


def verify_import(session=None) -> dict:
    """Verify import success by checking database state."""
    should_close = session is None
    session = session or SessionLocal()

    try:
        total = session.query(HybridPersona).count()
        personas = session.query(HybridPersona).order_by(HybridPersona.combination_number).all()

        # Check for duplicates
        persona_ids = [p.persona_id for p in personas]
        numbers = [p.combination_number for p in personas]

        dup_persona_ids = len(persona_ids) != len(set(persona_ids))
        dup_numbers = len(numbers) != len(set(numbers))

        # Check K-layer ranges
        k_layer_issues = []
        for p in personas:
            for layer in p.active_k_layers or []:
                if not (1 <= layer <= 98):
                    k_layer_issues.append(f"{p.persona_id}: invalid active layer {layer}")
            for layer in p.suppressed_k_layers or []:
                if not (1 <= layer <= 98):
                    k_layer_issues.append(f"{p.persona_id}: invalid suppressed layer {layer}")

        return {
            'total_count': total,
            'personas': personas,
            'duplicate_persona_ids': dup_persona_ids,
            'duplicate_numbers': dup_numbers,
            'k_layer_issues': k_layer_issues,
        }
    finally:
        if should_close:
            session.close()


def main():
    parser = argparse.ArgumentParser(
        description="Import hybrid personas from JSONL file to database"
    )
    parser.add_argument(
        '--input',
        type=Path,
        default=Path('data/hybrid_personas_raw.jsonl'),
        help='Input JSONL file (default: data/hybrid_personas_raw.jsonl)'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear existing personas before import'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Run verification after import'
    )

    args = parser.parse_args()

    # Import
    print(f"\n{'=' * 70}")
    print("PHASE 6: HYBRID PERSONAS BULK IMPORT")
    print(f"{'=' * 70}")

    stats = load_and_import_personas(args.input, clear_existing=args.clear)

    # Verify
    if args.verify:
        print("\nVerifying database state...")
        result = verify_import()
        print(f"  Total in DB:              {result['total_count']}")
        print(f"  Duplicate persona_ids:    {result['duplicate_persona_ids']}")
        print(f"  Duplicate numbers:        {result['duplicate_numbers']}")
        if result['k_layer_issues']:
            print(f"  K-layer validation issues:")
            for issue in result['k_layer_issues']:
                print(f"    - {issue}")
        else:
            print(f"  K-layer validation:       OK ✓")

    # Exit with status
    sys.exit(0 if stats.errors == 0 and stats.imported > 0 else 1)


if __name__ == '__main__':
    main()
