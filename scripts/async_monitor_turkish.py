#!/usr/bin/env python3
"""
Async monitoring for Turkish HPEP-100 file arrival.

Polls for the Turkish Word document every hour and auto-triggers the integration pipeline
when detected. Non-blocking, runs in background.

Usage:
    python scripts/async_monitor_turkish.py [--watch-dir DIR] [--interval HOURS] [--auto-run]

Options:
    --watch-dir DIR     Directory to monitor for .docx file (default: current dir)
    --interval HOURS    Check interval in hours (default: 1)
    --auto-run         Automatically run pipeline when file detected (default: prompt)
    --check-once       Check once and exit (for testing)

Environment:
    TURKISH_FILE_PATTERN    Glob pattern for Turkish file (default: "*turkish*.docx", "*HPEP*.docx")
    PIPELINE_OUTPUT_DIR     Where to save integration results (default: ./output)

Status file: .turkish_monitor_status.json
    Contains: {timestamp, file_detected, file_path, pipeline_status, last_check}
"""

import sys
import json
import time
import subprocess
import glob
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import os
import hashlib


def load_status() -> dict:
    """Load monitoring status from file."""
    status_file = Path(".turkish_monitor_status.json")
    if status_file.exists():
        try:
            with open(status_file, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "started_at": datetime.utcnow().isoformat() + "Z",
        "file_detected": False,
        "file_path": None,
        "file_hash": None,
        "pipeline_status": "waiting",
        "last_check": None,
        "checks": 0,
    }


def save_status(status: dict) -> None:
    """Save monitoring status to file."""
    status_file = Path(".turkish_monitor_status.json")
    with open(status_file, "w") as f:
        json.dump(status, f, indent=2)


def find_turkish_file(watch_dir: str) -> Optional[Path]:
    """
    Search for Turkish HPEP-100 file in directory.

    Looks for:
    - *turkish*.docx (case-insensitive)
    - *HPEP*.docx
    - hpep100_turkish.docx
    """
    watch_path = Path(watch_dir)

    patterns = [
        "*turkish*.docx",
        "*HPEP*.docx",
        "*hpep*.docx",
        "hpep100_tr.docx",
    ]

    for pattern in patterns:
        matches = list(watch_path.glob(pattern))
        if matches:
            # Return most recently modified
            return max(matches, key=lambda p: p.stat().st_mtime)

    return None


def compute_file_hash(filepath: Path) -> str:
    """Compute file hash."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def run_pipeline(
    turkish_file: Path,
    output_dir: Path,
    auto_run: bool = False,
) -> dict:
    """
    Run the Turkish integration pipeline.

    Steps:
    1. parse_turkish_docx.py → parsed.json
    2. translate_to_6langs.py → translated.json
    3. integrate_quiz_questions.py → update api/quiz_*.py + run tests

    Returns: {status, output_files, errors, duration}
    """
    output_dir.mkdir(exist_ok=True, parents=True)
    start_time = datetime.utcnow()

    results = {
        "status": "running",
        "phases": {},
        "errors": [],
        "duration_seconds": 0,
    }

    try:
        # Phase 1: Parse
        print("\n[1/3] Parsing Turkish document...")
        parsed_file = output_dir / "parsed_turkish.json"
        result = subprocess.run(
            [sys.executable, "scripts/parse_turkish_docx.py",
             str(turkish_file), str(parsed_file)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Parse failed:\n{result.stderr}")

        results["phases"]["parse"] = {
            "status": "success",
            "output": str(parsed_file),
        }
        print(f"✓ Parsed: {parsed_file}")

        # Phase 2: Translate
        print("\n[2/3] Translating to 6 languages...")
        translated_file = output_dir / "translated_6langs.json"
        result = subprocess.run(
            [sys.executable, "scripts/translate_to_6langs.py",
             str(parsed_file), str(translated_file)],
            capture_output=True,
            text=True,
            timeout=300,  # 5 min timeout for API calls
        )

        if result.returncode != 0:
            # Translation might fail if Gemini API unavailable; continue with warning
            print(f"⚠ Translation warning: {result.stderr[:200]}")
            results["phases"]["translate"] = {
                "status": "warning",
                "output": None,
                "message": "API call failed; skipping translation phase",
            }
            translated_file = parsed_file  # Use parsed file as fallback
        else:
            results["phases"]["translate"] = {
                "status": "success",
                "output": str(translated_file),
            }
            print(f"✓ Translated: {translated_file}")

        # Phase 3: Integrate
        print("\n[3/3] Integrating into quiz database...")
        result = subprocess.run(
            [sys.executable, "scripts/integrate_quiz_questions.py",
             str(translated_file)],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            results["errors"].append(result.stderr)
            results["phases"]["integrate"] = {
                "status": "failed",
                "error": result.stderr[:500],
            }
            print(f"✗ Integration failed")
        else:
            results["phases"]["integrate"] = {
                "status": "success",
            }
            print(f"✓ Integration complete")

        results["status"] = "success" if not results["errors"] else "partial"

    except subprocess.TimeoutExpired as e:
        results["status"] = "failed"
        results["errors"].append(f"Pipeline timeout: {e}")
    except Exception as e:
        results["status"] = "failed"
        results["errors"].append(str(e))

    results["duration_seconds"] = (
        datetime.utcnow() - start_time
    ).total_seconds()

    return results


def monitor_loop(
    watch_dir: str = ".",
    interval_hours: float = 1.0,
    auto_run: bool = False,
    check_once: bool = False,
) -> None:
    """
    Main monitoring loop.

    Polls every interval_hours for Turkish file arrival.
    When detected, triggers pipeline (or prompts if auto_run=False).
    """
    status = load_status()
    output_dir = Path(os.getenv("PIPELINE_OUTPUT_DIR", "./output"))

    interval_seconds = int(interval_hours * 3600)

    print(f"Turkish HPEP-100 Async Monitor")
    print(f"Watch directory: {watch_dir}")
    print(f"Check interval: {interval_hours} hour(s) ({interval_seconds}s)")
    print(f"Auto-run: {auto_run}")
    print(f"Status file: .turkish_monitor_status.json")
    print(f"Output dir: {output_dir}")
    print()

    iteration = 0
    while True:
        iteration += 1
        status["checks"] += 1
        status["last_check"] = datetime.utcnow().isoformat() + "Z"

        print(f"\n[{iteration}] Checking for Turkish file at {status['last_check']}")

        turkish_file = find_turkish_file(watch_dir)

        if turkish_file:
            file_hash = compute_file_hash(turkish_file)

            # Check if this is a new file
            if status.get("file_hash") != file_hash:
                status["file_detected"] = True
                status["file_path"] = str(turkish_file)
                status["file_hash"] = file_hash
                status["pipeline_status"] = "pending"

                print(f"✓ Turkish file detected: {turkish_file}")
                print(f"  Hash: {file_hash[:16]}...")
                print(f"  Size: {turkish_file.stat().st_size} bytes")

                save_status(status)

                # Run pipeline
                if auto_run or (
                    not check_once and input("\nRun integration pipeline? [y/n] ").lower() == "y"
                ):
                    print("\nStarting integration pipeline...")
                    result = run_pipeline(turkish_file, output_dir, auto_run)
                    status["pipeline_status"] = result["status"]
                    status["pipeline_result"] = result

                    save_status(status)

                    if result["status"] == "success":
                        print("\n✓ Pipeline completed successfully!")
                        print(f"  Duration: {result['duration_seconds']:.1f}s")
                        if not check_once:
                            print("\nMonitoring complete. File processed and stored.")
                            return
                    else:
                        print(f"\n✗ Pipeline failed: {result['status']}")
                        for error in result["errors"]:
                            print(f"  - {error}")
            else:
                print(f"ℹ File already processed: {turkish_file}")
        else:
            print("ℹ No Turkish file found yet. Waiting...")

        if check_once:
            break

        print(f"Next check in {interval_hours} hour(s)...")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Monitor for Turkish HPEP-100 file arrival and auto-integrate"
    )
    parser.add_argument(
        "--watch-dir",
        default=".",
        help="Directory to monitor (default: current)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Check interval in hours (default: 1)"
    )
    parser.add_argument(
        "--auto-run",
        action="store_true",
        help="Auto-run pipeline without prompting"
    )
    parser.add_argument(
        "--check-once",
        action="store_true",
        help="Check once and exit (for testing)"
    )

    args = parser.parse_args()

    try:
        monitor_loop(
            watch_dir=args.watch_dir,
            interval_hours=args.interval,
            auto_run=args.auto_run,
            check_once=args.check_once,
        )
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
        status = load_status()
        print(f"Final status: {status['pipeline_status']}")
        print(f"Checks performed: {status['checks']}")
