from __future__ import annotations

import json
import logging

from rag3.config import AppConfig
from rag3.generation import GenerativeReader

logger = logging.getLogger(__name__)


class ValidationAgent:
    def __init__(self, config: AppConfig, reader: GenerativeReader | None = None):
        self.config = config
        self.reader = reader or GenerativeReader(config)

    def validate_answer(self, query: str, context: str, generated_answer: str) -> dict[str, str]:
        if not self.config.validation_agent.enabled:
            return {
                "accuracy": "Skipped",
                "relevance": "Skipped",
                "suggestions": "Validation disabled in configuration.",
            }

        prompt = (
            "Return valid JSON with keys accuracy, relevance, suggestions. "
            "Evaluate answer quality against context.\n\n"
            f"Query: {query}\n\n"
            f"Context: {context}\n\n"
            f"Generated answer: {generated_answer}"
        )

        raw = self.reader.generate_answer(
            question="Validate this RAG answer",
            context=prompt,
            max_tokens=self.config.validation_agent.max_tokens,
        )

        try:
            parsed = json.loads(raw)
            return {
                "accuracy": str(parsed.get("accuracy", "Unknown")),
                "relevance": str(parsed.get("relevance", "Unknown")),
                "suggestions": str(parsed.get("suggestions", "Unknown")),
            }
        except json.JSONDecodeError:
            logger.warning("Validation response is not JSON: %s", raw)
            return {
                "accuracy": "Unknown",
                "relevance": "Unknown",
                "suggestions": "Validation output was not valid JSON.",
            }
