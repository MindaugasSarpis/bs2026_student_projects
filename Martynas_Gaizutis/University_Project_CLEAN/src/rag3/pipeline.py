from __future__ import annotations

import logging
from pathlib import Path

from rag3.config import AppConfig, get_default_config
from rag3.document_store import create_document_store
from rag3.generation import GenerativeReader
from rag3.indexing import DocumentIndexer
from rag3.retrieval import RetrieverModule
from rag3.validation import ValidationAgent

logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(self, config: AppConfig | None = None):
        self.config = config or get_default_config()
        self.document_store = create_document_store(self.config)

        self.indexer = DocumentIndexer(self.config, self.document_store)
        self.retriever = RetrieverModule(self.config, self.document_store)
        self.generative_reader: GenerativeReader | None = None
        self.validation_agent: ValidationAgent | None = None

    def index_documents(
        self,
        txt_folder_path: Path | None = None,
        pdf_folder_path: Path | None = None,
        word_folder_path: Path | None = None,
        excel_folder_path: Path | None = None,
        *,
        clear: bool = False,
    ) -> int:
        logger.info("Indexing documents")
        return self.indexer.index_documents(
            txt_folder_path,
            pdf_folder_path,
            word_folder_path,
            excel_folder_path,
            clear=clear,
        )

    def retrieve_documents(self, query: str) -> list[str]:
        docs = self.retriever.retrieve(query)
        return [doc.content for doc in docs]

    def generate_answer(self, query: str, context: str) -> str:
        if self.generative_reader is None:
            self.generative_reader = GenerativeReader(self.config)
        return self.generative_reader.generate_answer(query, context)

    def validate_answer(self, query: str, context: str, generated_answer: str) -> dict[str, str]:
        if self.validation_agent is None:
            self.validation_agent = ValidationAgent(self.config, self.generative_reader)
        return self.validation_agent.validate_answer(query, context, generated_answer)

    def run_pipeline(self, query: str) -> tuple[str, dict[str, str]]:
        documents = self.retrieve_documents(query)
        context = "\n\n".join(documents) if documents else "No relevant documents found."

        answer = self.generate_answer(query, context)
        report = self.validate_answer(query, context, answer)
        return answer, report
