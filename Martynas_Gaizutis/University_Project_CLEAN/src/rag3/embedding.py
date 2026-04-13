from __future__ import annotations

import logging

from haystack.components.embedders import SentenceTransformersTextEmbedder

from rag3.config import AppConfig, get_default_config

logger = logging.getLogger(__name__)


class Embedder:
    """Utility embedder kept for backward compatibility with legacy scripts."""

    def __init__(self, config: AppConfig | None = None):
        cfg = config or get_default_config()
        self.embedder = SentenceTransformersTextEmbedder(model=cfg.embedder.model)
        if cfg.embedder.warm_up:
            self.embedder.warm_up()

    def embed_query(self, query: str) -> list[float]:
        return self.embedder.run(query).get("embedding", [])

    def embed_documents(self, documents: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for doc in documents:
            vectors.append(self.embedder.run(doc).get("embedding", []))
        return vectors
