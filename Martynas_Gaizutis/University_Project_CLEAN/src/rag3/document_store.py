from __future__ import annotations

import logging

from haystack_integrations.document_stores.elasticsearch import ElasticsearchDocumentStore

from rag3.config import AppConfig

logger = logging.getLogger(__name__)


def create_document_store(config: AppConfig) -> ElasticsearchDocumentStore:
    es = config.elasticsearch
    auth = (es.username, es.password) if es.username and es.password else None

    document_store = ElasticsearchDocumentStore(
        hosts=[es.url],
        index=es.index,
        verify_certs=es.verify_certs,
        request_timeout=es.timeout,
        retry_on_timeout=es.retry_on_timeout,
        max_retries=es.max_retries,
        http_auth=auth,
    )

    logger.info("Connected to Elasticsearch index '%s' at %s", es.index, es.url)
    return document_store
