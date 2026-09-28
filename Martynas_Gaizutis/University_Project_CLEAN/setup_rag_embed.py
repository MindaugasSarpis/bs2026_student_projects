"""Legacy wrapper for embedding and Elasticsearch connection helpers.

Use `rag3.embedding` and `rag3.document_store` in new code.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rag3.config import get_default_config  # noqa: E402
from rag3.document_store import create_document_store  # noqa: E402
from rag3.embedding import Embedder  # noqa: E402


def connect_to_elasticsearch():
    config = get_default_config()
    document_store = create_document_store(config)
    return document_store, document_store.client


def connect_with_retry(retries=None, delay=None):
    return connect_to_elasticsearch()


__all__ = ["Embedder", "connect_to_elasticsearch", "connect_with_retry"]
