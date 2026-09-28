"""Legacy wrapper for `rag3.validation`.

Use `rag3.validation.ValidationAgent` for new code.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rag3.config import get_default_config  # noqa: E402
from rag3.validation import ValidationAgent as _ValidationAgent  # noqa: E402


class ValidationAgent(_ValidationAgent):
    def __init__(self, settings_manager=None):
        super().__init__(get_default_config())


__all__ = ["ValidationAgent"]
