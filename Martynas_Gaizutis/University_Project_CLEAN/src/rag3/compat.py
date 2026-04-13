from __future__ import annotations

from copy import deepcopy
from typing import Any

from rag3.config import AppConfig, get_default_config


class SettingsManager:
    """Backward-compatible dotted-key settings facade."""

    def __init__(self, config: AppConfig | None = None):
        self._config = config or get_default_config()
        self.settings = self._config.to_dict()

    def get(self, key: str, default: Any = None) -> Any:
        current: Any = self.settings
        for part in key.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def set(self, key: str, value: Any) -> None:
        parts = key.split(".")
        target = self.settings
        for part in parts[:-1]:
            if part not in target or not isinstance(target[part], dict):
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value

    def as_dict(self) -> dict[str, Any]:
        return deepcopy(self.settings)
