import sys
from pathlib import Path

# Add repo root to sys.path so tests can import api, needle, persona_math, persona_mcp
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))
