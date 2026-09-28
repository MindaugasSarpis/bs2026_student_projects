"""Legacy wrapper for `rag3.retrieval`.

Use `rag3.retrieval.RetrieverModule` for new code.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rag3.config import get_default_config  # noqa: E402
from rag3.document_store import create_document_store  # noqa: E402
from rag3.retrieval import RetrieverModule as _RetrieverModule  # noqa: E402


class RetrieverModule(_RetrieverModule):
    def __init__(self, document_store=None):
        config = get_default_config()
        store = document_store or create_document_store(config)
        super().__init__(config, store)


__all__ = ["RetrieverModule"]
