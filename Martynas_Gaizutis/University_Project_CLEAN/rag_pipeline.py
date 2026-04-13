"""Legacy entrypoint preserved for compatibility.

Use `python -m rag3.cli` for new usage.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rag3.cli import main  # noqa: E402

__all__ = ["RAGPipeline"]


def __getattr__(name):
    if name == "RAGPipeline":
        from rag3.pipeline import RAGPipeline

        return RAGPipeline
    raise AttributeError(name)


if __name__ == "__main__":
    main()
