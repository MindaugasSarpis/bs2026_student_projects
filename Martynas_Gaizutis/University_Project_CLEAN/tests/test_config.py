import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rag3.compat import SettingsManager
from rag3.config import get_default_config


class ConfigTests(unittest.TestCase):
    def test_settings_manager_get_set(self):
        manager = SettingsManager()
        manager.set("retriever.top_k", 9)
        self.assertEqual(manager.get("retriever.top_k"), 9)
        self.assertEqual(manager.get("missing.value", "fallback"), "fallback")

    def test_config_from_env(self):
        os.environ["ELASTICSEARCH_HOST"] = "127.0.0.1"
        config = get_default_config()
        self.assertEqual(config.elasticsearch.host, "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
