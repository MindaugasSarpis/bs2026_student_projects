"""RAG3: retrieval-augmented generation pipeline."""

from rag3.config import AppConfig, get_default_config

__all__ = ["AppConfig", "RAGPipeline", "get_default_config"]


def __getattr__(name):
    if name == "RAGPipeline":
        from rag3.pipeline import RAGPipeline

        return RAGPipeline
    raise AttributeError(name)
