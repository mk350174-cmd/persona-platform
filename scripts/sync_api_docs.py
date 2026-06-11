#!/usr/bin/env python3
"""
Sync API documentation with OpenAPI schema.

This script:
1. Extracts OpenAPI schema from FastAPI app
2. Parses existing API_DOCS.md
3. Detects missing/new/changed endpoints
4. Can auto-update API_DOCS.md with new endpoints

Usage:
    python scripts/sync_api_docs.py --check          # Check for drift (no changes)
    python scripts/sync_api_docs.py --update         # Auto-update with new endpoints
    python scripts/sync_api_docs.py --report report  # Generate HTML report
"""

import json
import sys
from pathlib import Path
from typing import Dict, Set, Tuple

# Add repo root to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_mock"


def extract_openapi_endpoints():
    """Extract all endpoints from OpenAPI schema."""
    from api.main import app

    openapi_schema = app.openapi()
    if not openapi_schema:
        return {}

    endpoints = {}
    paths = openapi_schema.get("paths", {})

    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method.lower() in ["get", "post", "put", "delete", "patch"]:
                endpoint_key = f"{method.upper()} {path}"
                endpoints[endpoint_key] = {
                    "path": path,
                    "method": method.upper(),
                    "summary": operation.get("summary", ""),
                    "description": operation.get("description", ""),
                    "tags": operation.get("tags", []),
                }

    return endpoints


def parse_api_docs():
    """Parse existing API_DOCS.md to extract documented endpoints."""
    api_docs_path = repo_root / "API_DOCS.md"

    if not api_docs_path.exists():
        return {}

    documented = {}
    with open(api_docs_path, "r") as f:
        content = f.read()

    # Extract endpoint patterns from markdown
    # Pattern: ```\nGET /path\n```
    import re

    # Pattern for code blocks with endpoints
    pattern = r"```\s*(GET|POST|PUT|DELETE|PATCH)\s+(/[\w\-/_{}]*)\s*```"
    matches = re.finditer(pattern, content, re.MULTILINE)

    for match in matches:
        method = match.group(1)
        path = match.group(2)
        endpoint_key = f"{method} {path}"
        documented[endpoint_key] = True

    return documented


def detect_drift(openapi_endpoints: Dict, documented_endpoints: Dict) -> Tuple[Set, Set, Set]:
    """Detect drift between OpenAPI schema and documentation."""
    openapi_keys = set(openapi_endpoints.keys())
    documented_keys = set(documented_endpoints.keys())

    missing = openapi_keys - documented_keys  # In OpenAPI, not in docs
    extra = documented_keys - openapi_keys    # In docs, not in OpenAPI
    synced = openapi_keys & documented_keys  # In both

    return missing, extra, synced


def generate_endpoint_section(endpoint_key: str, endpoint_info: Dict) -> str:
    """Generate markdown section for an endpoint."""
    method = endpoint_info["method"]
    path = endpoint_info["path"]
    summary = endpoint_info["summary"]
    description = endpoint_info.get("description", "")
    tags = endpoint_info.get("tags", [])

    section = f"\n## {method} `{path}`\n\n"

    if summary:
        section += f"**Summary:** {summary}\n\n"

    if description:
        section += f"{description}\n\n"

    if tags:
        section += f"**Tags:** {', '.join(tags)}\n\n"

    section += "**Status:** Auto-generated endpoint (needs manual documentation)\n\n"
    section += "- **Request:** (TODO: Document request parameters)\n"
    section += "- **Response:** (TODO: Document response fields)\n"
    section += "- **Examples:** (TODO: Add request/response examples)\n"
    section += "- **Errors:** (TODO: Document possible error responses)\n"

    return section


def check_drift(openapi_endpoints: Dict, documented_endpoints: Dict) -> bool:
    """Check for documentation drift. Returns True if drift found."""
    missing, extra, synced = detect_drift(openapi_endpoints, documented_endpoints)

    if not missing and not extra:
        print("✅ No drift detected. API documentation is in sync.")
        print(f"📊 {len(synced)} endpoints documented and synchronized.")
        return False

    print("⚠️  Documentation drift detected!")
    print(f"📊 Total endpoints in OpenAPI: {len(openapi_endpoints)}")
    print(f"📊 Total endpoints in docs: {len(documented_endpoints)}")
    print(f"📊 Synchronized: {len(synced)}")

    if missing:
        print(f"\n❌ Missing from documentation ({len(missing)}):")
        for endpoint in sorted(missing):
            print(f"  - {endpoint}")

    if extra:
        print(f"\n⚠️  Extra in documentation ({len(extra)}):")
        for endpoint in sorted(extra):
            print(f"  - {endpoint}")

    return True  # Drift found


def update_docs(openapi_endpoints: Dict, documented_endpoints: Dict) -> bool:
    """Auto-update API_DOCS.md with new endpoints."""
    missing, extra, synced = detect_drift(openapi_endpoints, documented_endpoints)

    if not missing:
        print("✅ All endpoints documented. No updates needed.")
        return True

    print(f"📝 Updating API_DOCS.md with {len(missing)} new endpoints...")

    api_docs_path = repo_root / "API_DOCS.md"

    # Read existing file
    with open(api_docs_path, "r") as f:
        content = f.read()

    # Append new endpoints
    new_endpoints_section = "\n\n# Auto-Generated Endpoints\n\n"
    new_endpoints_section += "The following endpoints are auto-generated from the OpenAPI schema.\n"
    new_endpoints_section += "They require manual documentation to complete.\n"

    for endpoint_key in sorted(missing):
        endpoint_info = openapi_endpoints[endpoint_key]
        new_endpoints_section += generate_endpoint_section(endpoint_key, endpoint_info)

    # Append to file
    with open(api_docs_path, "a") as f:
        f.write(new_endpoints_section)

    print(f"✅ Updated {api_docs_path}")
    print(f"📝 Added {len(missing)} endpoints to auto-generated section")

    return True


def generate_report(openapi_endpoints: Dict, documented_endpoints: Dict, output_file: str = None):
    """Generate HTML report of documentation coverage."""
    missing, extra, synced = detect_drift(openapi_endpoints, documented_endpoints)

    coverage_percent = (len(synced) / len(openapi_endpoints) * 100) if openapi_endpoints else 0

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>API Documentation Coverage Report</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .good {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .bad {{ color: #dc3545; }}
        .endpoint-list {{ margin: 20px 0; }}
        .endpoint {{ background: #f9f9f9; padding: 10px; margin: 5px 0; border-left: 3px solid #ccc; }}
        .endpoint.documented {{ border-left-color: #28a745; }}
        .endpoint.missing {{ border-left-color: #dc3545; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f5f5f5; }}
        .metric {{ display: inline-block; margin-right: 20px; }}
        .metric-number {{ font-size: 24px; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>API Documentation Coverage Report</h1>
    <p>Generated from OpenAPI schema and API_DOCS.md</p>

    <div class="summary">
        <h2>Coverage Summary</h2>
        <div class="metric">
            <div class="metric-number" style="color: #28a745;">{len(synced)}</div>
            <div>Documented</div>
        </div>
        <div class="metric">
            <div class="metric-number" style="color: #dc3545;">{len(missing)}</div>
            <div>Missing</div>
        </div>
        <div class="metric">
            <div class="metric-number">{coverage_percent:.1f}%</div>
            <div>Coverage</div>
        </div>
    </div>

    <h2>Endpoints by Status</h2>
    <table>
        <tr>
            <th>Endpoint</th>
            <th>Status</th>
            <th>Summary</th>
        </tr>
"""

    # Add documented endpoints
    for endpoint_key in sorted(synced):
        endpoint_info = openapi_endpoints[endpoint_key]
        summary = endpoint_info.get("summary", "")
        html += f"""        <tr class="endpoint documented">
            <td><code>{endpoint_key}</code></td>
            <td><span class="good">✅ Documented</span></td>
            <td>{summary}</td>
        </tr>
"""

    # Add missing endpoints
    for endpoint_key in sorted(missing):
        endpoint_info = openapi_endpoints[endpoint_key]
        summary = endpoint_info.get("summary", "")
        html += f"""        <tr class="endpoint missing">
            <td><code>{endpoint_key}</code></td>
            <td><span class="bad">❌ Missing</span></td>
            <td>{summary}</td>
        </tr>
"""

    html += """    </table>
</body>
</html>
"""

    if output_file:
        output_path = repo_root / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(html)
        print(f"📊 Report generated: {output_path}")
    else:
        print(html)

    return True


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Sync API documentation with OpenAPI schema")
    parser.add_argument("--check", action="store_true", help="Check for drift (no changes)")
    parser.add_argument("--update", action="store_true", help="Auto-update with new endpoints")
    parser.add_argument("--report", type=str, help="Generate HTML report to file")

    args = parser.parse_args()

    # Extract endpoints
    print("🔍 Extracting OpenAPI endpoints...")
    openapi_endpoints = extract_openapi_endpoints()
    print(f"✅ Found {len(openapi_endpoints)} endpoints in OpenAPI schema")

    print("📖 Parsing API_DOCS.md...")
    documented_endpoints = parse_api_docs()
    print(f"✅ Found {len(documented_endpoints)} documented endpoints")

    # Default to --check if no action specified
    if not args.check and not args.update and not args.report:
        args.check = True

    # Perform requested action
    if args.check:
        drift_found = check_drift(openapi_endpoints, documented_endpoints)
        return 1 if drift_found else 0

    if args.update:
        success = update_docs(openapi_endpoints, documented_endpoints)
        return 0 if success else 1

    if args.report:
        generate_report(openapi_endpoints, documented_endpoints, args.report)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
