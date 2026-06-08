"""
needle.pipeline — bulk bundling of the persona library.

Both ``BulkBundler`` and ``PlaceholderFactory`` are torch-free (untrained bundles use
stdlib placeholders), so this package imports and runs without torch / the gguf lib.
"""

from .bulk_bundler import BulkBundler
from .placeholder_factory import PlaceholderFactory

__all__ = ["BulkBundler", "PlaceholderFactory"]
