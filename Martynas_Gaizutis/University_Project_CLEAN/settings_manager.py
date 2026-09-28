"""Backward-compatible settings module for legacy imports.

Use `rag3.config` for new code.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rag3.compat import SettingsManager  # noqa: E402

__all__ = ["SettingsManager"]
