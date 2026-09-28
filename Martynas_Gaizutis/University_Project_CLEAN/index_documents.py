"""Legacy wrapper for document indexing.

Use `rag3.indexing.DocumentIndexer` or `python -m rag3.cli index`.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rag3.config import get_default_config  # noqa: E402
from rag3.document_store import create_document_store  # noqa: E402
from rag3.indexing import DocumentIndexer as _DocumentIndexer  # noqa: E402
from rag3.pipeline import RAGPipeline  # noqa: E402


class DocumentIndexer(_DocumentIndexer):
    def __init__(self, document_store=None):
        config = get_default_config()
        store = document_store or create_document_store(config)
        super().__init__(config, store)


if __name__ == "__main__":
    pipeline = RAGPipeline()
    count = pipeline.index_documents(clear=False)
    print(f"Indexed {count} documents")
