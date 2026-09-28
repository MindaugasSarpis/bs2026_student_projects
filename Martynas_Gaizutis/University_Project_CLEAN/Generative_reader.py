"""Legacy wrapper for `rag3.generation`.

Use `rag3.generation.GenerativeReader` for new code.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rag3.config import get_default_config  # noqa: E402
from rag3.generation import GenerativeReader as _GenerativeReader  # noqa: E402


class GenerativeReader(_GenerativeReader):
    def __init__(self, settings_manager=None):
        config = get_default_config()
        super().__init__(config)


__all__ = ["GenerativeReader"]
