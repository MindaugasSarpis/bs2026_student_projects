"""Legacy Streamlit entrypoint.

Run with: `streamlit run ui_module.py`
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rag3.ui import render_app  # noqa: E402

render_app()
