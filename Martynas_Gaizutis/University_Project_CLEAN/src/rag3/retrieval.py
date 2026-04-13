from __future__ import annotations

import logging
import time
from typing import Any

from haystack_integrations.components.retrievers.elasticsearch import ElasticsearchBM25Retriever

from rag3.config import AppConfig

logger = logging.getLogger(__name__)


class RetrieverModule:
    def __init__(self, config: AppConfig, document_store):
        self.config = config
        self.document_store = document_store
        self.index_name = config.elasticsearch.index

        self.top_k = config.retriever.top_k
        self.retries = config.retriever.retries
        self.delay_seconds = config.retriever.delay_seconds

        self.retriever = self._initialize_retriever()

    def _initialize_retriever(self) -> ElasticsearchBM25Retriever:
        for attempt in range(1, self.retries + 1):
            try:
                retriever = ElasticsearchBM25Retriever(document_store=self.document_store)
                logger.info("Retriever initialized with top_k=%s", self.top_k)
                return retriever
            except Exception as exc:
                if attempt == self.retries:
                    raise
                backoff = self.delay_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "Retriever init failed (attempt %s/%s): %s. Retrying in %ss",
                    attempt,
                    self.retries,
                    exc,
                    backoff,
                )
                time.sleep(backoff)

        raise RuntimeError("Retriever initialization failed")

    def validate_document_store(self) -> bool:
        try:
            if not self.document_store.client.ping():
                return False
            self.document_store.client.count(index=self.index_name)
            return True
        except Exception:
            return False

    def retrieve(self, query: str, top_k: int | None = None) -> list[Any]:
        if not query.strip():
            return []

        if not self.validate_document_store():
            logger.error("Document store is unavailable")
            return []

        count = top_k if top_k is not None else self.top_k
        result = self.retriever.run(query=query, top_k=count)
        documents = result.get("documents", [])
        logger.info("Retrieved %s documents", len(documents))
        return documents
